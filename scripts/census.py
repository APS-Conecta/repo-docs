#!/usr/bin/env python3
"""The census and the onboarding tripwire (org L8-02 / L8-01), extracted from
sweep.yml so the lookup can be self-tested. The census = baseline keys (minus
two infrastructure entries) union OWN_APPS variable names from gestion's
12-apps.sh — the suite's own registry, so a repo cannot ship without being in
it.

OWN_APPS keys are provisioning variable names and carry no canonical casing
(`intravox`), while baseline keys carry the GitHub-canonical spelling of the
repo (`IntraVox`, baseline.json:106). GitHub resolves repo names
case-insensitively, so the clone succeeds either way — but the baseline
membership test is a Python `in` over dict keys, an exact match, and it failed
the 2026-09-28 sweep on exactly such a pair. The lookup here is therefore
case-insensitive: each census name folds onto the baseline key it matches
case-insensitively (baseline is the canon authority, so clone dirs and the
membership test line up on its spelling), and a name with NO case-insensitive
baseline match survives the fold untouched — that survivor is the tripwire, a
repo that joined the suite without canonizing (L8-01).

The fold also dedups the union: a case-sensitive `sort -u` kept both spellings
and the loop visited the repo twice.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ORG = "APS-Conecta"
INFRA = {".github", "repo-docs"}   # baseline keys that are not suite repos


def sh(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True)


def own_apps(registry: Path) -> list[str]:
    """The variable-name half of every `key=url` entry in 12-apps.sh's OWN_APPS
    (the sed/tr/cut pipeline the workflow used to inline, now testable)."""
    m = re.search(r'^OWN_APPS="(.*)"$', registry.read_text(), re.M)
    if not m:
        sys.exit(f"census: no OWN_APPS assignment found in {registry}")
    return [entry.split("=", 1)[0] for entry in m.group(1).split() if entry]


def resolve(name: str, baseline_keys: list[str]) -> str:
    """Fold `name` onto the baseline key it matches case-insensitively; no
    match → `name` unchanged, so the onboarding tripwire survives the fold."""
    for key in baseline_keys:
        if key.lower() == name.lower():
            return key
    return name


def census(own: list[str], baseline_keys: list[str]) -> list[str]:
    """Baseline keys ∪ OWN_APPS names, folded case-insensitively — `sort -u`
    alone kept `intravox` and `IntraVox` as two entries."""
    return sorted({resolve(n, baseline_keys) for n in [*own, *baseline_keys]})


def run(gestion: str, baseline_path: str, root: str = None) -> None:
    """Clone gestion (the registry), build the census, clone every repo in it,
    and fail on the first census repo without a baseline key. Every clone lands
    under `root` — the sweep points it at RUNNER_TEMP so the census never nests
    inside the repo-docs checkout: nested there, `check --all` walked repo-docs
    itself with the whole org inside it (2026-10-06, run 37457227748)."""
    base = Path(root).resolve() if root else Path.cwd()
    gpath = Path(gestion)
    if not gpath.is_absolute():
        gpath = base / gestion
    if not gpath.exists():
        gpath.parent.mkdir(parents=True, exist_ok=True)
        sh(["gh", "repo", "clone", f"{ORG}/gestion", str(gpath), "--", "-q"])
    baseline = json.loads(Path(baseline_path).read_text())
    keys = [k for k in baseline if k not in INFRA]
    names = census(own_apps(gpath / "provisioning" / "phases" / "12-apps.sh"), keys)
    for r in names:
        rpath = base / r
        if not rpath.exists():
            rpath.parent.mkdir(parents=True, exist_ok=True)
            sh(["gh", "repo", "clone", f"{ORG}/{r}", str(rpath), "--", "-q"])
        if r not in baseline:
            print(f"::error::census repo '{r}' has no baseline key — canonize it: "
                  f"scripts/docs.py check {r} --fix, then scripts/docs.py check "
                  f"--all --save-baseline (org L8-01)")
            sys.exit(1)
    print("census cloned: " + " ".join(names))


# ---------------------------------------------------------------- selftest

def selftest() -> None:
    # The live defect this module exists for (the 2026-09-28 red sweep):
    # gestion's OWN_APPS carries the variable name `intravox`, baseline.json:106
    # carries the GitHub-canonical `IntraVox`. Both directions are asserted,
    # per the docs.py selftest convention (scripts/docs.py:1696).
    keys = ["IntraVox"]
    own = ["intravox"]

    # Fail direction — the defect class: an exact `in` over baseline keys misses
    # the pair, which is what the workflow's inline membership test used to do.
    assert "intravox" not in keys, "fixture must actually mismatch in exact case"

    # Pass direction — the fix: resolution is case-insensitive and yields the
    # baseline spelling, so clone dir and membership test line up on the canon.
    assert resolve("intravox", keys) == "IntraVox", "lookup must fold case"
    assert resolve("intravox", keys) in keys, "the folded name must hit baseline"

    # The fold dedups the union — a case-sensitive `sort -u` visited the repo twice.
    assert census(own, keys) == ["IntraVox"], census(own, keys)

    # The tripwire survives the fold: an OWN_APPS name with no baseline match at
    # ANY casing stays itself and fires the onboarding error (L8-01).
    assert resolve("newapp", keys) == "newapp", "folding must not swallow a new repo"
    assert census(["newapp"], keys) == ["IntraVox", "newapp"], census(["newapp"], keys)

    # OWN_APPS extraction: the variable-name half of each `key=url` entry.
    with tempfile.TemporaryDirectory() as td:
        reg = Path(td) / "12-apps.sh"
        reg.write_text('OWN_APPS="intravox=https://github.com/APS-Conecta/IntraVox.git '
                       'other=https://example.invalid/other.git"\n')
        assert own_apps(reg) == ["intravox", "other"], own_apps(reg)

    # run() must clone under --root, never beside the caller: the 2026-10-06 sweep
    # let the whole census land inside the repo-docs checkout, and `check --all`
    # then audited repo-docs with every repo nested in it. Assert destinations,
    # not clones: `sh` is stubbed to record argv and materialize targets, so no
    # network is touched (the docs.py selftest patches `gh` the same way).
    with tempfile.TemporaryDirectory() as td:
        checkout, root = Path(td) / "checkout", Path(td) / "census-root"
        checkout.mkdir()
        (checkout / "baseline.json").write_text(json.dumps({"demo": [], ".github": []}))
        clones = []

        def fake_sh(argv):
            if argv[:3] != ["gh", "repo", "clone"]:
                return
            clones.append(Path(argv[4]))
            Path(argv[4]).mkdir(parents=True, exist_ok=True)
            if argv[3].endswith("/gestion"):        # the registry rides the clone
                reg = Path(argv[4]) / "provisioning" / "phases" / "12-apps.sh"
                reg.parent.mkdir(parents=True, exist_ok=True)
                reg.write_text('OWN_APPS="demo=https://example.invalid/demo.git"\n')

        real_sh = globals()["sh"]
        globals()["sh"] = fake_sh
        try:
            run(str(root / "gestion"), str(checkout / "baseline.json"), root=str(root))
        finally:
            globals()["sh"] = real_sh
        assert [c.name for c in clones] == ["gestion", "demo"], clones
        assert all(c.parent.resolve() == root.resolve() for c in clones), \
            "census clones must land under --root, not beside the caller"
        assert not any(c.is_relative_to(checkout) for c in clones), clones
        assert (root / "demo").is_dir(), "the clone must exist where run() put it"
    print("census: ok")


def main(argv=None):
    p = argparse.ArgumentParser(prog="census.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="build the census, clone it, enforce the tripwire")
    r.add_argument("--gestion", default="gestion",
                   help="path of the gestion clone (cloned there when absent)")
    r.add_argument("--baseline", default="baseline.json")
    r.add_argument("--root", default=None,
                   help="directory the census clones into (default: the cwd — the "
                        "weekly sweep passes $RUNNER_TEMP/census so clones land "
                        "outside the repo-docs checkout)")
    sub.add_parser("selftest", help="assert the case-insensitive lookup, both directions")
    a = p.parse_args(argv)
    if a.cmd == "run":
        run(a.gestion, a.baseline, a.root)
    else:
        selftest()


if __name__ == "__main__":
    main()
