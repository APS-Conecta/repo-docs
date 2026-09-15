#!/usr/bin/env python3
"""repo-docs — documentation control for APS-Conecta.

Audit first, scaffold second. Everything extensible is a table:
profiles/*.json for policy; CHECKS, FACTS, SETTINGS for rules.
If tuning needs a function body edited, the seam is wrong.

Stdlib only. Every subprocess call takes an argv list — paths contain spaces.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import string
import subprocess
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _resource(name: str) -> Path:
    """Resolve a resource directory from EITHER location this file runs from.

    As `repo-docs/scripts/docs.py` the resources sit one level up. As the copy each repo vendors at
    `.github/repo-docs.py` they sit beside it, because there is no level up to speak of. Assuming the
    first meant `PROFILES` was `<repo>/profiles/`, which no repo has, so `P` was `{}` and every
    vendored invocation died in argparse with `KeyError: 'levels'` before doing any work. The docs
    workflow in every repository therefore advertised a gate that had never run once — confirmed by a
    real failed run on aps-conecta-web PR #1."""
    for base in (_HERE.parent, _HERE):
        if (base / name).is_dir():
            return base / name
    return _HERE.parent / name


SKILL = _HERE.parent
CANON_DIR = _resource("canon")
PUBLIC_DIR = _resource("public")
PROFILES = _resource("profiles")

# Which canon this copy of the checker was rendered from. `render` writes the digest here on the way
# out, so every vendored copy carries one and the copy in canon/ keeps this empty — which is how a
# canon source says it is the original rather than a render of one. Read by `canon-stamp`.
#
# Deliberately not a `string.Template` placeholder: this whole file is rendered, so a placeholder
# here would also be substituted inside the comparison below that reads it. Every dollar-sigil token
# in this file is substituted on the way out, which is why none of the prose in it writes one.
CANON_STAMP = "cf22b906ce06"

# ---- craft vs decision (ADR 0002) --------------------------------------------------
# Every rule below is craft: true of documentation anywhere. Every rule's PARAMETERS are
# decisions one owner made, and they live in profiles/<owner>.json, never here.

# Regexes that encode craft, not policy — how Markdown is shaped, not what it should say.
ABSOLUTE_PATH = re.compile(r"(?<![\w])/(?:srv|home|Users|mnt)/[\w./-]{3,}")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EMAIL_ALLOW = re.compile(r"@users\.noreply\.github\.com$|@example\.(com|org)$|^git@")
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$", re.M)
BOLD_LABEL = re.compile(r"\*\*([^*\n]{2,80}?)\*\*")
TABLE_CELL = re.compile(r"^\|([^|\n]+)\|", re.M)
OFF_LIMITS = re.compile(r"do not touch|don'?t touch|never touch|do not modify|off-limits", re.I)
PROJECT_VOICE = re.compile(r"\b(app|apps|repo|repos|repositor(?:y|io)|aplicaci[oó]n)\b", re.I)
OWN_LICENCE = re.compile(r"\bproprietary\b|all rights reserved|todos los derechos|\bpropietario\b", re.I)
# The organisation name is written out, never as a template placeholder. `render` substitutes with
# `string.Template`, whose escape for a literal dollar is a doubled dollar and not a backslash, so
# the backslash form this line used to carry reached every vendored copy with its backslash intact —
# and a leading backslash-A is the start-of-string anchor, so the alternative matched nothing at all.
# Writing the name out also makes this line render identically in canon and in every copy, which is
# what stops the defect coming back. `[- ]` covers both spellings; the lookahead drops
# `github.com/APS-Conecta/<repo>` URLs, which name a location rather than the subject of a sentence.
# Asserted both ways in `selftest`.
SELF_REF = re.compile(r"\bour\b|\bwe\b|this (?:project|organisation|organization|repo)|"
                      r"APS[- ]Conecta\b(?![-/])|licence:|license:|nuestr|c[oó]digo propio", re.I)
# The brand marks ARE all-rights-reserved under AGPL 7(e) — that claim is correct and must survive.
MARKS = re.compile(r"logo|lockup|favicon|wordmark|\bmarks?\b|trademark|§ ?7\(e\)", re.I)
PROHIBITION = re.compile(r"\bnever\b|\bdo not\b|\bdon'?t\b|\bmust not\b|\bno longer\b", re.I)
# Past tense is history, not a claim: "our output was proprietary" recounts, "our output is
# proprietary" asserts. 'was' was deliberately removed from RETIRED because it matched ordinary prose
# and hid a real phantom command — that lesson is about *retirement* markers on any sentence. Here the
# whole sentence is about our licence already, so tense is the only thing left to read.
PAST_LICENCE = re.compile(r"\bwas\b|\bwere\b|\bused to\b|\buntil\b|\bpredates?\b|\bhad been\b", re.I)

CHECKS: list = []
FACTS: dict = {}
# A probe that could not run must never read as a check that passed. Anything recorded here makes the
# run degraded, and a degraded run may not be written to the baseline: doing so records everything it
# failed to evaluate as "resolved". One flaky API call silently retired four real findings once.
DEGRADED: list = []
# Rules that did not run this pass. Their previous findings are UNKNOWN, never resolved.
SKIPPED_RULES: set = set()
SETTINGS: dict = {}

P: dict = {}          # active profile — set by use_profile()
ROOT = Path.cwd()
ORG = ""
HOLDER = ""


def _merge(base: dict, over: dict) -> dict:
    """Lists concatenate so a profile EXTENDS craft (leak patterns, stack markers);
    scalars override so it can contradict a default outright."""
    for k, v in over.items():
        if k.startswith("_comment"):
            continue
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        elif isinstance(v, list) and isinstance(base.get(k), list):
            base[k] = base[k] + v
        else:
            base[k] = v
    return base


def managed_owners() -> list:
    return sorted(p.stem for p in PROFILES.glob("*.json") if not p.stem.startswith("_"))


def load_profile(owner: str):
    """None means UNMANAGED — absence of policy is a refusal, never a default (ADR 0002)."""
    f = PROFILES / f"{owner.lower()}.json"
    if not f.exists():
        return None
    base = json.loads((PROFILES / "_base.json").read_text())
    prof = _merge(base, json.loads(f.read_text()))
    cfg = SKILL / "config.json"          # machine-local overrides; never vendored
    if cfg.exists():
        _merge(prof, {k: v for k, v in json.loads(cfg.read_text()).items()
                      if k in ("root", "holder")})
    for env, key in (("REPO_DOCS_ROOT", "root"), ("REPO_DOCS_HOLDER", "holder")):
        if os.environ.get(env):
            prof[key] = os.environ[env]
    return prof


def use_profile(owner: str) -> bool:
    global P, ROOT, ORG, HOLDER
    prof = load_profile(owner)
    if prof is None:
        return False
    P = prof
    ROOT = Path(prof.get("root") or Path.cwd())
    ORG = prof.get("org") or owner
    HOLDER = prof.get("holder") or ""
    return True


def rx(pairs, flags=re.I):
    """Compile a profile's [pattern, payload] pairs at use, not at import."""
    return [(re.compile(p, flags), payload) for p, payload in pairs]


use_profile(os.environ.get("REPO_DOCS_ORG", "aps-conecta"))


# ---------------------------------------------------------------- primitives

def sh(argv, cwd=None):
    """Run argv. Never a shell string — paths contain spaces."""
    if argv and argv[0] == "git" and "-C" in argv:
        # `apps/` is chowned to the container uid (33) so Nextcloud can write it, which makes host
        # git refuse those clones as "dubious ownership". Every git call then fails identically to
        # having no remote, so the repo left the audit reading as absent — territorio was
        # unaudited this way. Scoped to the one path we were asked about, and
        # only ever for reads.
        argv = [argv[0], "-c", f"safe.directory={argv[argv.index('-C') + 1]}"] + argv[1:]
    p = subprocess.run(argv, cwd=str(cwd) if cwd else None,
                       capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def gh(*args):
    """gh api wrapper. Returns parsed JSON, raw text, or None when the call fails."""
    code, out, _ = sh(["gh", *args])
    if code != 0:
        DEGRADED.append("gh " + " ".join(str(a) for a in args[:3]))
        return None
    try:
        return json.loads(out)
    except (ValueError, TypeError):
        return out or None


def denied(path: str) -> bool:
    """Vendored trees are excluded by git itself — they are committed as tarballs, so
    `git ls-files` never surfaces them. A measured denylist excluded 0 files across all
    four repos, so it was deleted rather than maintained. Nested repos are handled
    separately, by halting the walk."""
    return "node_modules/" in path.replace(os.sep, "/")


class Finding:
    __slots__ = ("rule", "severity", "file", "line", "msg", "fixed")

    def __init__(self, rule, severity, file, line, msg, fixed=False):
        self.rule, self.severity = rule, severity
        self.file, self.line, self.msg, self.fixed = file, line, msg, fixed

    def __str__(self):
        loc = f"{self.file}:{self.line}" if self.line else (self.file or "-")
        tag = "FIXED" if self.fixed else self.severity.upper()
        return f"{tag:<7} {self.rule:<20} {loc:<44} {self.msg}"


def rule(name, severity, offline=True):
    """Register a check. Adding a rule = one function + one decorator line.
    offline=False marks rules needing org-scoped auth — excluded from the CI gate (Q7)."""
    def deco(fn):
        CHECKS.append((name, severity, offline, fn))
        return fn
    return deco


def fact(key, offline=True):
    """Register a canonical fact: an authority probe plus doc claim extraction."""
    def deco(fn):
        FACTS[key] = (offline, fn)
        return fn
    return deco


def setting(key, guard=None, scope="any"):
    """Register a GitHub setting the tool may change under --apply-settings.
    scope='public' marks features GitHub only offers on public repos (secret scanning
    and private vulnerability reporting need GHAS on a private repo) — applying them
    to a private repo is not a failure, it is not applicable."""
    def deco(fn):
        SETTINGS[key] = (fn, guard, scope)
        return fn
    return deco


# ---------------------------------------------------------------- discovery

def repo_name(path: Path):
    """Identity comes from the remote URL, NEVER the directory name.
    'custom apps/Territorio' -> 'territorio'."""
    code, url, _ = sh(["git", "-C", str(path), "config", "--get", "remote.origin.url"])
    if code != 0 or not url:
        return None, None
    m = re.search(r"[:/]([^/]+)/([^/]+?)(?:\.git)?$", url)
    return (m.group(1), m.group(2)) if m else (None, None)


def discover(root: Path = None) -> dict:
    """Walk root, read each .git remote, keep repos whose owner has a profile.
    An owner with no profile is UNMANAGED and never touched (ADR 0002)."""
    root = Path(root) if root else ROOT
    managed = {o.lower() for o in managed_owners()}
    found, nested, unmanaged, unreadable = {}, {}, {}, []
    for dirpath, dirnames, _ in os.walk(root):
        if denied(dirpath):
            dirnames[:] = []
            continue
        if ".git" not in dirnames:
            continue
        d = Path(dirpath)
        org, name = repo_name(d)
        if org and org.lower() in managed:
            found[name] = d
        elif org:
            unmanaged[name] = org
        else:
            # A repo we cannot name is not the same as a repo that is not ours. Silence here is how
            # two repos went unaudited while the run still exited green.
            unreadable.append(str(d))
        dirnames.remove(".git")
    for name, path in found.items():
        for other, opath in found.items():
            if other != name and str(path).startswith(str(opath) + os.sep):
                nested[name] = other
    seen = {}
    for owner in unmanaged.values():        # counts, not a wall of third-party clones
        seen[owner] = seen.get(owner, 0) + 1
    return {"repos": {k: str(v) for k, v in sorted(found.items())},
            "nested": nested, "profiles": managed_owners(),
            "unmanaged": dict(sorted(seen.items(), key=lambda kv: -kv[1])),
            "unreadable": sorted(unreadable)}


def resolve(target: str) -> Path:
    """Accept a repo name or a path."""
    p = Path(target).expanduser()
    if (p / ".git").exists():
        p = p.resolve()
        owner, _ = repo_name(p)
        if owner and not use_profile(owner):
            sys.exit(f"repo-docs: {owner!r} is unmanaged — no profiles/{owner.lower()}.json. "
                     f"Managed: {', '.join(managed_owners())}")
        return p
    repos = discover()["repos"]
    if target in repos:
        return Path(repos[target])
    sys.exit(f"repo-docs: no clone for {target!r}. Known: {', '.join(repos) or '(none)'}")


def missing_clones() -> list:
    remote = gh("repo", "list", ORG, "--limit", "100", "--json", "name", "--jq", ".[].name")
    if not remote:
        return []
    have = set(discover()["repos"])
    return [r for r in str(remote).split("\n") if r and r not in have]


# ---------------------------------------------------------------- inventory

def tracked_md(repo: Path) -> list:
    """git-tracked *.md minus nested repos. The Governed Surface."""
    code, out, _ = sh(["git", "-C", str(repo), "ls-files", "-z", "--", "*.md", "*.markdown"])
    if code != 0:
        return []
    rel = [f for f in out.split("\0") if f and not denied(f)]

    def inside_nested_repo(r: str) -> bool:
        # Every ancestor, not just the first segment. All three app clones live at `apps/<id>`, so
        # testing only `r.split("/")[0]` asked whether `apps/.git` existed — it does not, and the
        # boundary held by luck: gestion tracks nothing under `apps/`. CONTEXT.md promises this
        # boundary unconditionally.
        parts = r.split("/")[:-1]
        return any((repo.joinpath(*parts[:i + 1]) / ".git").exists() for i in range(len(parts)))

    return [r for r in rel if not inside_nested_repo(r)]


def governed(repo: Path) -> list:
    # A file git still tracks but the working tree no longer has is a real state — mid-rename, or a
    # deletion not yet staged. Every rule then read it and the whole run died on a traceback instead
    # of reporting one file. Absence is reported by `tracked-not-present`, never crashed on.
    return [f for f in tracked_md(repo) if (repo / f).exists()]


def tracked_but_absent(repo: Path) -> list:
    return [f for f in tracked_md(repo) if not (repo / f).exists()]


def detect_stacks(repo: Path) -> list:
    out = []
    for marker, label in P["stack_markers"].items():
        if (repo / marker).exists() or list(repo.glob(f"*/{marker}"))[:1]:
            out.append(label)
    return sorted(set(out))


def archetype(repo: Path, stacks: list, name: str = None) -> str:
    declared = (P.get("repo_archetypes") or {}).get(name or "")
    if declared:
        return declared             # no stack marker distinguishes a CLI from a library
    if (repo / "profile" / "README.md").exists():
        return "org-profile"
    if "wordpress-theme" in stacks:
        return "website"
    if "nextcloud-app" in stacks:
        return "nextcloud-app"
    if "docker" in stacks:
        return "app"
    return "library"


def find_health(repo: Path) -> dict:
    """Resolve each health file in GitHub's precedence order. First hit wins."""
    hits = {}
    for name in P["health_names"]:
        for d in P["health_dirs"]:
            cand = repo / d / name if d != "." else repo / name
            if cand.exists():
                hits[name] = str(cand.relative_to(repo))
                break
    if (repo / ".github" / "ISSUE_TEMPLATE").is_dir():
        hits["ISSUE_TEMPLATE"] = ".github/ISSUE_TEMPLATE"
    for name in ("README.md", "LICENSE", "CHANGELOG.md"):
        if (repo / name).exists():
            hits[name] = name
    for extra in ("docs/index.md", ".githooks/pre-commit", ".github/workflows/docs.yml", "docs/adr",
                  "profile/README.md"):     # the org level requires it, so it must be detectable
        if (repo / extra).exists():
            hits[extra] = extra
    return hits


SPDX_NORM = (("agpl", "agpl"), ("lgpl", "lgpl"), ("gpl", "gpl"), ("mit", "mit"),
             ("apache", "apache"), ("mpl", "mpl"), ("mozilla", "mpl"), ("bsd", "bsd"),
             ("isc", "isc"), ("unlicense", "unlicense"), ("proprietary", "proprietary"),
             ("all rights reserved", "proprietary"), ("sil ofl", "ofl"), ("ofl", "ofl"))


def norm_licence(text):
    """SPDX id, licence name or file header -> one family token."""
    if not text:
        return None
    t = str(text).lower()
    for needle, label in SPDX_NORM:
        if needle in t:
            return label
    return "other"


def licence_sites(repo: Path) -> dict:
    """Every place this repo DECLARES its own licence. A repo has one licence; if these
    disagree, at least one of them is lying to a packaging tool."""
    sites = {}
    lic = repo / "LICENSE"
    if lic.exists():
        sites["LICENSE"] = license_kind(repo)
    info = repo / "appinfo" / "info.xml"
    if info.exists():
        m = re.search(r"<licen[cs]e>([^<]+)</licen[cs]e>", info.read_text(errors="replace"), re.I)
        if m:
            sites["appinfo/info.xml"] = norm_licence(m.group(1))
    for man in ("composer.json", "package.json"):
        f = repo / man
        if not f.exists():
            continue
        try:
            d = json.loads(f.read_text(errors="replace"))
        except ValueError:
            continue
        if d.get("license"):
            sites[man] = norm_licence(d["license"] if isinstance(d["license"], str)
                                      else " ".join(d["license"]))
    return sites


def inventory(repo: Path) -> list:
    """Third-party licences actually present. (component, licence, source)."""
    out = []
    lock = repo / "composer.lock"
    if lock.exists():
        try:
            for pkg in json.loads(lock.read_text(errors="replace")).get("packages", []):
                out.append((pkg.get("name", "?"), norm_licence(" ".join(pkg.get("license", []))),
                            "composer.lock", "runtime"))
        except ValueError:
            pass
    pj = repo / "package.json"
    if pj.exists():
        try:
            d = json.loads(pj.read_text(errors="replace"))
        except ValueError:
            d = {}
        for name, phase in ([(n, "runtime") for n in d.get("dependencies", {})]
                            + [(n, "dev") for n in d.get("devDependencies", {})]):
            meta = repo / "node_modules" / name / "package.json"
            lic = None
            if meta.exists():
                try:
                    lic = json.loads(meta.read_text(errors="replace")).get("license")
                except ValueError:
                    lic = None
            out.append((name, norm_licence(lic) if lic else None, "package.json", phase))
    for sub in sorted((repo / "apps").glob("*")) if (repo / "apps").is_dir() else []:
        if sub.is_dir() and not (sub / ".git").exists():
            k = license_kind(sub)
            if k:
                out.append((f"apps/{sub.name}", k, "vendored", "runtime"))
    for m in re.finditer(r"image:\s*([\w./-]+):", (repo / "compose.yaml").read_text(errors="replace")
                         if (repo / "compose.yaml").exists() else ""):
        out.append((m.group(1), None, "compose image", "runtime"))
    return out


def license_kind(repo: Path):
    lic = repo / "LICENSE"
    if not lic.exists():
        return None
    head = lic.read_text(errors="replace")[:900].lower()
    if "all rights reserved" in head or "proprietary" in head:
        return "proprietary"
    for k, label in (("gnu affero", "agpl"), ("mit license", "mit"),
                     ("apache license", "apache"), ("gnu general public", "gpl"),
                     ("gnu lesser", "lgpl"), ("mozilla public", "mpl"),
                     ("bsd 3-clause", "bsd"), ("bsd 2-clause", "bsd")):
        if k in head:
            return label
    return "other"


def doc_lang(repo: Path, files: list) -> str:
    es = en = 0
    # Docs deliberately not in the policy language are a decision, so the list lives in the profile.
    exempt = tuple(P.get("doc_language_exempt", ()))
    for f in files:
        if exempt and f.endswith(exempt):
            continue
        for _, text in HEADING.findall((repo / f).read_text(errors="replace")):
            words = re.findall(r"[a-záéíóúñ]+", text.lower())
            if any(w in set(P["es_stopwords"]) for w in words):
                es += 1
            elif words:
                en += 1
    if not (es or en):
        return "n/a"
    return "es" if es > en else ("mixed" if es else "en")


def default_branch(repo: Path) -> str:
    """The repo's DEFAULT branch, never the one checked out. Canon substitution, the PR base and the
    branch-name rule all want this one. Reading HEAD instead meant that working on a feature branch
    — the only way CONTRIBUTING allows — baked that branch's name into docs.yml on `--fix` and
    opened pull requests against itself. Offline: origin/HEAD is unset in half these clones."""
    code, out, _ = sh(["git", "-C", str(repo), "symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
    if code == 0 and out:
        return out.split("/", 1)[-1]
    for cand in ("main", "master"):
        if sh(["git", "-C", str(repo), "rev-parse", "--verify", "-q",
               f"refs/remotes/origin/{cand}"])[0] == 0:
            return cand
    _, cur, _ = sh(["git", "-C", str(repo), "symbolic-ref", "--short", "HEAD"])
    return cur or "main"


def scan(repo: Path) -> dict:
    stacks = detect_stacks(repo)
    files = governed(repo)
    _, branch, _ = sh(["git", "-C", str(repo), "symbolic-ref", "--short", "HEAD"])
    org, name = repo_name(repo)
    nested = [str(p.parent.relative_to(repo)) for p in repo.glob("*/*/.git")] + \
             [str(p.parent.relative_to(repo)) for p in repo.glob("*/.git") if p.parent != repo]
    readme = repo / "README.md"
    sections = []
    if readme.exists():
        rt = readme.read_text(errors="replace")
        # a section may be a heading, a bold lead-in, or a file-map table row —
        # gestion states Status in a blockquote and the licence in a table cell
        sections = [t.lower() for _, t in HEADING.findall(rt)] \
            + [t.lower() for t in BOLD_LABEL.findall(rt)] \
            + [t.lower() for t in TABLE_CELL.findall(rt)]
    return {
        "org": org, "repo": name, "path": str(repo), "branch": branch,
        "default_branch": default_branch(repo),
        "stacks": stacks, "archetype": archetype(repo, stacks, name),
        "license_kind": license_kind(repo), "health": find_health(repo),
        "governed": files, "docs": sorted(f for f in files if f.startswith("docs/")),
        "adrs": sorted(f for f in files if "/adr/" in f or f.startswith("adr/")),
        "readme_sections": sections, "nested": sorted(set(nested)),
        "doc_lang": doc_lang(repo, files),
        "has_ci": (repo / ".github" / "workflows").is_dir(),
    }


# ---------------------------------------------------------------- canon

_STAMP_LINE = re.compile(r'^CANON_STAMP = "[^"]*"$', re.M)


def _canon_digest(sources: dict) -> str:
    """sha256[:12] over {canon-relative name: text}, with the stamp line blanked in each first.

    The stamp is written INTO a canon source, so hashing the bytes as they lie makes the digest a
    function of itself: write the stamp, the digest moves, the stamp is stale again, forever. Blanking
    the one line is what makes the comparison converge. Every other byte still counts, or the digest
    would report a canon it never read."""
    h = hashlib.sha256()
    for rel in sorted(sources):
        h.update(rel.encode())
        h.update(_STAMP_LINE.sub('CANON_STAMP = ""', sources[rel]).encode())
    return h.hexdigest()[:12]


def canon_stamp() -> str:
    """The digest of canon as it stands — empty when canon is not beside this checker.

    Seeds are excluded. A seed is written once and then belongs to the repository (CONTEXT.md), so
    editing `canon/LICENSE` is not engine drift and must not age every vendored copy at once."""
    if not CANON_DIR.is_dir():
        return ""
    seeds = set(P.get("canon_seed_only") or ())
    return _canon_digest({rel: (CANON_DIR / rel).read_text(errors="replace")
                          for rel in P["canon"]
                          if rel not in seeds and (CANON_DIR / rel).exists()})


def canon_vars(facts: dict) -> dict:
    return {"org": ORG, "repo": facts.get("repo") or "",
            "branch": facts.get("default_branch") or "main",
            "holder": HOLDER, "year": "2026", "canon_stamp": canon_stamp(),
            "code_owners": P.get("code_owners") or ""}


def contract(archetype: str) -> list:
    """The Section Contract: (key, prompt) the archetype owes. Generates the outline,
    prompts the author, and gates the result — one definition, so they cannot drift."""
    keys = list(P["core_sections"]) + \
        P["archetypes"].get(archetype, {}).get("extra", [])
    prompts = P.get("section_prompts", {})
    return [(k, prompts.get(k, "")) for k in keys]


def outline(archetype: str, repo_name_: str) -> str:
    """A README the author fills in, not a placeholder they must invent structure for."""
    lines = [f"# {repo_name_}", ""]
    for key, prompt in contract(archetype):
        lines += [f"## $SECTION_{key.upper()}", "", f"> {prompt}" if prompt else "", ""]
    lines += ["<!-- Every $SECTION_ heading and $PLACEHOLDER must be replaced before merge;",
              f"     `docs.py check {repo_name_}` fails while any remain. -->"]
    return "\n".join(lines) + "\n"


def render(name: str, vars_: dict) -> str:
    """Unknown placeholders survive verbatim so they stay visible as unfilled.

    The canon stamp is written after substitution, not as a placeholder: the checker reads its own
    `CANON_STAMP` to report what it is, and a placeholder would be substituted inside that comparison
    too, leaving every stamped copy calling itself unstamped."""
    src = (CANON_DIR / name).read_text()
    out = string.Template(src).safe_substitute(vars_)
    stamp = vars_.get("canon_stamp")
    return _STAMP_LINE.sub(f'CANON_STAMP = "{stamp}"', out) if stamp else out


def harvest(exemplar: Path) -> list:
    """Refresh canon/ from the exemplar. One convention, one home."""
    written = []
    org, name = repo_name(exemplar)
    if not name:
        sys.exit(f"repo-docs: {exemplar} has no origin remote — refusing to harvest from a "
                 f"repository I cannot name")
    # The dollar is assembled at runtime, never written literally. These four ARE the variables
    # `render` supplies, and this file is rendered into every repository, so a bare `$` followed by
    # `holder` here is substituted on the way out: the vendored copy's table then replaces the
    # owner's name with the owner's name, and `harvest` in a vendored copy would write real values
    # into canon instead of placeholders. `string.Template` leaves a lone `$` untouched — it
    # matches none of its three forms — so `D` survives rendering, and so does this comment.
    D = "$"
    subs = [(re.escape(HOLDER), f"{D}holder"), (rf"\b{re.escape(name or '')}\b", f"{D}repo"),
            (re.escape(ORG), f"{D}org"), (r"\b2026\b", f"{D}year")]
    for canon_rel, repo_rel in P["canon"].items():
        src = exemplar / repo_rel
        if canon_rel in P["canon_no_harvest"] or not src.exists():
            continue  # authored here, not derived from the exemplar
        text = src.read_text(errors="replace")
        for pat, repl in subs:
            if pat:
                text = re.sub(pat, repl, text)
        dst = CANON_DIR / canon_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text)
        written.append(canon_rel)
    return written


def required(level: str, org_mode: bool, archetype: str = None) -> tuple:
    # Derived from the archetype, not only the operator flag. `check --all` passes ONE flag for eight
    # repos, so keying on it alone meant a sweep could never be right about both the org repo and the
    # other seven: it demanded a LICENSE and a CODEOWNERS that this tool's own layout.md forbids
    # there, while identifying the repo BY the profile/README.md it reported missing.
    if org_mode or archetype == "org-profile":
        return P["org_level"]
    return P["levels"][level]


def gaps(facts: dict, level: str, org_mode: bool) -> list:
    have = set(facts["health"])
    if facts.get("archetype") != "org-profile":
        # GitHub serves these from the org's public .github repository to every repo without its own,
        # so demanding a local copy asks for the duplication org-before-repo exists to prevent.
        #
        # Read from the profile, NOT by looking for a sibling .github clone: this same file runs
        # vendored in CI, where no sibling exists, and inferring "absent" there failed three repos on
        # a checkout layout rather than on their documentation. The presence of the org files is
        # verified where it belongs — `org_level` requires all five when auditing `.github` itself.
        have |= set(P.get("org_inheritable") or [])
    return [r for r in required(level, org_mode, facts.get("archetype")) if r not in have]


def scaffold(repo: Path, level: str, org_mode: bool, write: bool) -> list:
    facts = scan(repo)
    vars_ = canon_vars(facts)
    out = []
    for missing in gaps(facts, level, org_mode):
        # A requirement may name a DIRECTORY (ISSUE_TEMPLATE); every canon entry under it
        # must be written, not just the first match.
        matches = [c for c, r in P["canon"].items() if r.endswith(missing) or missing in r]
        for canon_rel in (matches or [None]):
            dest = repo / (P["canon"].get(canon_rel) or missing)
            if dest.exists():
                continue
            out.append(str(dest.relative_to(repo)))
            if not write:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            if canon_rel:
                dest.write_text(render(canon_rel, vars_))
                if dest.name == "pre-commit":
                    dest.chmod(0o755)
            elif missing == "README.md":
                dest.write_text(outline(facts["archetype"], facts["repo"] or dest.parent.name))
            else:
                # In org mode the shareable documents are already authored, in public/. This branch
                # used to run first and claim the filename with a placeholder, so the block that
                # copied public/ found dst.exists() and never fired — the org repo was published
                # carrying "$PLACEHOLDER — authored, never templated" as its CONTRIBUTING and
                # SECURITY. Nothing caught it, because an untracked file is not yet governed.
                pub = (PUBLIC_DIR / missing) if org_mode else None
                if pub is not None and pub.exists():
                    dest.write_text(string.Template(pub.read_text()).safe_substitute(vars_))
                else:
                    title = Path(missing).stem.replace("-", " ").replace("_", " ").title()
                    dest.write_text(f"# {title}\n\n$PLACEHOLDER — authored, never templated.\n")
    return out


# ---------------------------------------------------------------- facts

def _claims(repo: Path, files: list, pattern: re.Pattern, norm, subj=None):
    """subj groups claims that are about different things — 'Nextcloud 34' and
    'Redis 8' are complementary, not contradictory."""
    out = []
    for f in files:
        if is_history(f):
            # A changelog that records a corrected fact necessarily still contains the old value —
            # the entry saying team size was wrong quotes "a 3-person team" in order to retire it.
            # Dated history states what WAS true; only live prose makes a claim.
            continue
        for i, line in enumerate((repo / f).read_text(errors="replace").splitlines(), 1):
            m = pattern.search(line)
            if m:
                out.append((f, i, line.strip()[:90], norm(m), subj(m) if subj else None))
    return out


@fact("team_size", offline=False)
def _f_team(ctx):
    pat = re.compile(r"\b(three|two|3|2)[- ]person team\b|\bsingle developer\b|\bsolo\b", re.I)

    def norm(m):
        t = m.group(0).lower()
        return 1 if ("single" in t or "solo" in t) else (3 if ("three" in t or "3" in t) else 2)
    members = gh("api", f"orgs/{ORG}/members", "--jq", ".[].login")
    authority = len(str(members).split("\n")) if members else None
    return authority, _claims(ctx["path"], ctx["files"], pat, norm)


@fact("licence")
def _f_licence(ctx):
    """OUR licence only. docs/LICENSING.md enumerates third-party licences by design
    (ADR 0007 keeps those notices) — reading them as our declaration is a false positive."""
    pat = re.compile(r"\b(MIT|Apache|GPL|proprietary|all rights reserved)\b", re.I)
    def norm(m):
        t = m.group(1).lower()
        return "proprietary" if t in ("proprietary", "all rights reserved") else t
    own = [f for f in ctx["files"] if f == "README.md" or f.startswith("LICENSE")]
    selfref = re.compile(r"\bour\b|this (project|repo|repository|code)|^\s*licen[cs]e\b"
                         r"|\bLICENSE\b", re.I)
    claims = [c for c in _claims(ctx["path"], own, pat, norm) if selfref.search(c[2])]
    return ctx["facts"]["license_kind"], claims


@fact("default_branch", offline=False)
def _f_branch(ctx):
    pat = re.compile(r"\bbranch off `(\w+)`|\bpushes to `(\w+)`")
    api = gh("api", f"repos/{ORG}/{ctx['facts']['repo']}", "--jq", ".default_branch")
    return api, _claims(ctx["path"], ctx["files"], pat, lambda m: m.group(1) or m.group(2))


@fact("stack_versions")
def _f_versions(ctx):
    compose = next((ctx["path"] / c for c in ("compose.yaml", "compose.yml")
                    if (ctx["path"] / c).exists()), None)
    if not compose:
        return None, []
    alias = P.get("stack_version_components") or {}
    if not alias:
        return None, []
    names = "|".join(re.escape(k) for k in alias)
    real = dict(re.findall(rf"image:\s*({names}):(\d+)", compose.read_text()))
    authority = {alias[k]: v for k, v in real.items()}
    pat = re.compile(r"\b(" + "|".join(re.escape(v) for v in alias.values()) + r")\s+(\d+)")
    # subject = the component, so 'Nextcloud 34' and 'Redis 8' never look contradictory
    return authority, _claims(ctx["path"], ctx["files"], pat,
                              lambda m: {m.group(1): m.group(2)},
                              subj=lambda m: m.group(1))


@fact("repo_visibility", offline=False)
def _f_vis(ctx):
    api = gh("api", f"repos/{ORG}/{ctx['facts']['repo']}", "--jq", ".private")
    pat = re.compile(r"repository is \*{0,2}(private|public)\*{0,2}", re.I)
    authority = {"true": "private", "false": "public"}.get(str(api).lower())
    return authority, _claims(ctx["path"], ctx["files"], pat, lambda m: m.group(1).lower())


DOC_COMMAND = re.compile(r"\b(make|npm run|yarn|composer)\s+([a-zA-Z][\w:-]*)")


def available_commands(repo: Path) -> set:
    """Every command this repo can actually run: Makefile targets, npm and composer scripts."""
    have = set()
    mk = repo / "Makefile"
    if mk.exists():
        have |= {f"make {t}" for t in
                 re.findall(r"^([a-zA-Z][\w-]*)\s*:(?!=)", mk.read_text(errors="replace"), re.M)}
    for man, prefix in (("package.json", "npm run"), ("composer.json", "composer")):
        f = repo / man
        if not f.exists():
            continue
        try:
            scripts = json.loads(f.read_text(errors="replace")).get("scripts", {}) or {}
        except ValueError:
            continue
        have |= {f"{prefix} {k}" for k in scripts}
        if prefix == "npm run":
            have |= {f"yarn {k}" for k in scripts}
    return have


def gated_commands(repo: Path) -> set:
    """Commands some automated gate actually runs. Verification, not intention."""
    gated = set()
    wf = repo / ".github" / "workflows"
    for f in sorted(wf.glob("*.y*ml")) if wf.is_dir() else []:
        for m in DOC_COMMAND.finditer(f.read_text(errors="replace")):
            gated.add(f"{m.group(1)} {m.group(2)}")
    hook = repo / ".githooks" / "pre-commit"
    if hook.exists():
        for m in DOC_COMMAND.finditer(hook.read_text(errors="replace")):
            gated.add(f"{m.group(1)} {m.group(2)}")
    return gated


# 'was' was here and matched ordinary prose, silently suppressing a real phantom in
# BUGS.md. A retirement marker must be unambiguous.
RETIRED = re.compile(r"\b(deleted|removed|retired|superseded|no longer|dropped)\b", re.I)


def is_history(f: str) -> bool:
    """Dated history is exempt: its date is the label. CONTRIBUTING.md says so."""
    return bool(re.search(r"(^|/)(CHANGELOG|BUGS|ROADMAP)\.md$|/adr/", f))


def _code_spans(line: str) -> list:
    """Character ranges inside backticks. 'make it' in prose is the English verb;
    `make it` in code voice is a command. Only the second is documentation."""
    return [(m.start(), m.end()) for m in re.finditer(r"`[^`]+`", line)]


def documented_commands(repo: Path, files: list) -> dict:
    """command -> first (file, line) that tells a reader to run it.
    Only code-voice mentions count: inside backticks, or inside a fenced block."""
    found = {}
    for f in files:
        fenced = False
        lines = (repo / f).read_text(errors="replace").splitlines()
        for i, line in enumerate(lines, 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            spans = _code_spans(line)
            for m in DOC_COMMAND.finditer(line):
                in_code = fenced or any(a < m.start() and m.end() <= b for a, b in spans)
                if not in_code:
                    continue
                # Markdown prose wraps, so a retirement note routinely lands on the NEXT
                # line. Read the surrounding paragraph, never the single line.
                window = "\n".join(lines[max(0, i - 2):i + 2])
                cmd = f"{m.group(1)} {m.group(2)}"
                found.setdefault(cmd, (f, i, bool(RETIRED.search(window))))
    return found


# ---------------------------------------------------------------- rules

@rule("missing-required", "error")
def _r_missing(ctx):
    for miss in gaps(ctx["facts"], ctx["level"], ctx["org_mode"]):
        yield Finding("missing-required", "error", None, None, f"absent: {miss}")


@rule("github-metadata", "error", offline=False)
def _r_gh_meta(ctx):
    """A repository's description is the most-read documentation it has — it appears in every list,
    every search result and the organisation's front page — and nothing governed it. Three were
    single-tenant, three were Spanish and one was empty, none of it visible to this tool."""
    name = ctx["facts"]["repo"]
    if not name:
        return
    meta = gh("api", f"repos/{ORG}/{name}", "--jq", "{d:.description}")
    if not isinstance(meta, dict):
        return                      # gh() already recorded the failure; never guess from silence
    desc = (meta.get("d") or "").strip()
    if not desc:
        yield Finding("github-metadata", "error", None, None,
                      "no repository description — the first documentation anyone reads")
        return
    for pat, why in (P.get("single_tenant") or []):
        if re.search(pat, desc, re.I):
            yield Finding("github-metadata", "error", None, None,
                          f"description {why}: {desc[:70]!r}")
    want = P.get("doc_language")
    words = re.findall(r"[a-záéíóúñ]+", desc.lower())
    hits = sum(w in set(P["es_stopwords"]) for w in words)
    # A description is a handful of words, so two stopwords is a high bar: "Sitio web de APS Conecta"
    # scores one. Short text gets the lower threshold.
    if want == "en" and (hits >= 2 or (hits >= 1 and len(words) <= 6)):
        yield Finding("github-metadata", "warn", None, None,
                      f"description is Spanish; repo docs are {want!r}: {desc[:60]!r}")


@rule("tracked-not-present", "error")
def _r_tracked_absent(ctx):
    """Reported rather than crashed on: every rule used to read the file and the run died on a
    traceback, naming a path with no explanation of why the whole audit stopped."""
    for f in tracked_but_absent(ctx["path"]):
        yield Finding("tracked-not-present", "error", f, None,
                      "git tracks it but the working tree does not have it — stage the deletion "
                      "or restore the file")


@rule("license-posture", "error")
def _r_licence(ctx):
    want = P.get("licence_posture")
    if not want or ctx["facts"]["archetype"] == "org-profile":
        return                      # no posture declared, or a profile repo that ships no code
    kind = ctx["facts"]["license_kind"]
    if kind is None:
        yield Finding("license-posture", "error", "LICENSE", None,
                      "no LICENSE — and a licence cannot be inherited from the org .github")
    elif kind != want:
        yield Finding("license-posture", "error", "LICENSE", None,
                      f"licence is {kind!r}; this owner mandates {want!r} org-wide")


@rule("licence-declaration", "error")
def _r_licence_sites(ctx):
    """One repo, one licence. LICENSE, appinfo/info.xml, composer.json and package.json
    are four declarations of the same fact and are read by different tools."""
    want = P.get("licence_posture")
    sites = licence_sites(ctx["path"])
    if len(set(sites.values())) > 1:
        for where, kind in sorted(sites.items()):
            yield Finding("licence-declaration", "error", where, None,
                          f"declares {kind!r}; this repo declares "
                          f"{len(set(sites.values()))} different licences")
    if want:
        for where, kind in sorted(sites.items()):
            if kind and kind != want:
                yield Finding("licence-declaration", "error", where, None,
                              f"declares {kind!r}, owner mandates {want!r}")
    if sites and "LICENSE" not in sites:
        yield Finding("licence-declaration", "error", None, None,
                      f"declares a licence in {', '.join(sites)} but ships no LICENSE file")


@rule("licence-prose", "error")
def _r_licence_prose(ctx):
    """The LICENSE file was checked; the prose describing it was not. That is how the organisation
    kept calling its own code proprietary after relicensing — on its only public page, in this
    skill's own rules, and in the org-default CONTRIBUTING template — while `check` reported this
    repo as clean. Four declarations of the licence were verified and the sentence was not."""
    want = P.get("licence_posture")
    if not want or want == "proprietary":
        return
    notices = tuple(P.get("notices_doc") or ())
    for f in ctx["files"]:
        # The notices document exists to reproduce other people's licence text, much of which says
        # "all rights reserved" about work that is not ours.
        if is_history(f) or (notices and f.endswith(notices)):
            continue
        lines = (ctx["path"] / f).read_text(errors="replace").splitlines()
        for i, line in enumerate(lines, 1):
            if not OWN_LICENCE.search(line):
                continue
            if (MARKS.search(line) or PROHIBITION.search(line) or RETIRED.search(line)
                    or PAST_LICENCE.search(line)):
                continue        # the carve-out, a prohibition, a retirement marker, or history
            # A claim spans a sentence, not a line: look at the neighbours for who it is about.
            if not SELF_REF.search(" ".join(lines[max(0, i - 2):i + 1])):
                continue
            yield Finding("licence-prose", "error", f, i,
                          f"describes our own code as proprietary; posture is {want!r}")


@rule("licence-inventory", "warn")
def _r_licence_inventory(ctx):
    """Third-party licences present in the tree must appear in the notices document,
    and the notices document must not name components that are gone."""
    docs_ = P.get("notices_doc")
    docs_ = [docs_] if isinstance(docs_, str) else (docs_ or [])
    doc = next((d for d in docs_ if (ctx["path"] / d).exists()), docs_[0] if docs_ else None)
    inv = inventory(ctx["path"])
    inv = [t for t in inv if t[3] == "runtime"]   # dev deps are never distributed
    unknown = [c for c, lic, _, _ in inv if lic is None]
    if unknown:
        yield Finding("licence-inventory", "warn", None, None,
                      f"{len(unknown)} dependencies have no machine-readable licence "
                      f"(e.g. {', '.join(unknown[:3])}) — record them by hand")
    if not doc or not (ctx["path"] / doc).exists():
        if inv:
            yield Finding("licence-inventory", "warn", doc, None,
                          f"{len(inv)} third-party components and no notices document")
        return
    text = (ctx["path"] / doc).read_text(errors="replace").lower()
    families = sorted({lic for _, lic, _, _ in inv if lic})
    for fam in families:
        if fam not in text:
            yield Finding("licence-inventory", "warn", doc, None,
                          f"{fam!r} is used by a dependency but absent from the notices")


# `licence-copyleft` was deleted here. It asked whether copyleft dependencies were safe under a
# PROPRIETARY posture, and ADR 0010 made the organisation AGPL-3.0-or-later, so its first line
# returned before it could ever fire again. The question that replaces it — is a dependency
# *incompatible* with AGPL-3.0-or-later, GPL-2.0-only being the one that bites — cannot be asked of
# `inventory()`, which resolves licences to coarse families: `gpl` alone does not say whether the
# "or later" option exists to take. Documenting a check we cannot run would be the exact defect this
# skill exists to find, so there is no rule here until the inventory carries SPDX identifiers.


@rule("canon-drift", "error")
def _r_canon(ctx):
    vars_ = canon_vars(ctx["facts"])
    # The org repo is world-readable and only some canon may be published there: CODEOWNERS names a
    # person, the hook and workflow describe our gate, and GitHub cannot inherit any of the three
    # anyway (ADR-0012 in gestion). Without this, --fix on the org repo published all four.
    publishable = P.get("canon_org") or []
    is_org = ctx["org_mode"] or ctx["facts"].get("archetype") == "org-profile"
    if not CANON_DIR.is_dir():
        # The vendored CI copy has profiles beside it but not canon/, so every source file is absent
        # and this rule would compare nothing and pass. Say so instead: an unevaluated rule that
        # reports green is the defect this whole pass has been removing.
        DEGRADED.append("rule 'canon-drift': canon/ is not available to this copy of the checker")
        SKIPPED_RULES.add("canon-drift")
        print("SKIP    canon-drift          canon/ not vendored beside this checker — not evaluated")
        return
    for canon_rel, repo_rel in P["canon"].items():
        dst, src = ctx["path"] / repo_rel, CANON_DIR / canon_rel
        if canon_rel in P["canon_seed_only"] or not src.exists():
            continue
        if is_org and canon_rel not in publishable:
            continue
        # A hook that is not executable is not a hook. `scaffold` chmods; `--fix` only wrote the text,
        # so every hook it installed was inert — 5 of 6 repos, recorded in git as 100644, which means
        # every clone got a dead secret-guard while CONTRIBUTING.md documented it as a gate. Mode is
        # part of the artifact, so a wrong mode is drift.
        needs_exec = canon_rel in (P.get("canon_executable") or [])
        if not dst.exists():
            # Absence is drift too. A directory requirement is satisfied by its canon
            # members, never by the directory existing with one file in it.
            if ctx["fix"]:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(render(canon_rel, canon_vars(ctx["facts"])))
                if needs_exec:
                    dst.chmod(0o755)
                yield Finding("canon-drift", "error", repo_rel, None, "added from canon/", True)
            else:
                yield Finding("canon-drift", "error", repo_rel, None,
                              f"missing; canon/{canon_rel} defines it")
            continue
        want = render(canon_rel, vars_)
        inert = needs_exec and not os.access(dst, os.X_OK)
        if dst.read_text(errors="replace") == want and not inert:
            continue
        if ctx["fix"]:
            dst.write_text(want)
            if needs_exec:
                dst.chmod(0o755)
            yield Finding("canon-drift", "error", repo_rel, None,
                          "mode fixed — it was not executable" if inert else "restored from canon/",
                          True)
        elif inert:
            yield Finding("canon-drift", "error", repo_rel, None,
                          "present but NOT EXECUTABLE — it never runs; --fix sets the mode")
        else:
            yield Finding("canon-drift", "error", repo_rel, None,
                          f"differs from canon/{canon_rel} — --fix restores it")


@rule("canon-stamp", "warn")
def _r_canon_stamp(ctx):
    """`canon-drift` needs both sides, and a vendored copy has only one: no repository carries
    `canon/` (ADR 0004), so the rule that keeps eight copies from becoming eight versions reports
    SKIP in the seven places the copies actually live. The stamp is what a copy carries instead —
    the digest of the canon it was rendered from, written by `render`. Here, where canon IS present,
    it names *which* engine a repository is on rather than only that its bytes differ; where canon is
    absent it is at least printed, so a CI log records the version it ran."""
    want = canon_stamp()
    rel = P["canon"].get("repo-docs.py")
    dst = (ctx["path"] / rel) if rel else None
    have = ""
    if dst and dst.exists():
        m = _STAMP_LINE.search(dst.read_text(errors="replace"))
        have = m.group(0).split('"')[1] if m else ""
    if not want:
        # Unevaluated must never read as green (ADR 0004), but the stamp is still a fact worth
        # printing: it is the only record of which canon this copy came from.
        DEGRADED.append("rule 'canon-stamp': canon/ is not available to this copy of the checker")
        SKIPPED_RULES.add("canon-stamp")
        print(f"SKIP    {'canon-stamp':<20} no canon/ beside this checker; copy is stamped "
              f"{CANON_STAMP or '(unstamped)'}")
        return
    if not dst or not dst.exists():
        return                  # canon-drift already reports an absent vendored checker
    if have == want:
        return
    yield Finding("canon-stamp", "warn", rel, None,
                  f"rendered from canon {have or '(unstamped)'}; canon is now {want} "
                  f"— --fix re-renders it")


@rule("secrets", "error")
def _r_secrets(ctx):
    if shutil.which("gitleaks"):
        code, out, _ = sh(["gitleaks", "detect", "--no-banner", "--redact",
                           "--source", str(ctx["path"])])
        if code != 0:
            yield Finding("secrets", "error", None, None,
                          f"gitleaks flagged findings: {out.splitlines()[-1][:80] if out else ''}")
        return
    blocked = re.compile(r"(^|/)(\.env(\..+)?|CREDENTIALS\.local\.md)$|\.(pem|key|p12)$|(^|/)id_rsa")
    code, out, _ = sh(["git", "-C", str(ctx["path"]), "ls-files"])
    for f in out.split("\n"):
        if f and blocked.search(f) and not f.endswith(".env.example"):
            yield Finding("secrets", "error", f, None, "secret-shaped file is tracked")
    high = re.compile(r"(ghp_[A-Za-z0-9]{20,}|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16})")
    for f in ctx["files"]:
        for i, line in enumerate((ctx["path"] / f).read_text(errors="replace").splitlines(), 1):
            if high.search(line):
                yield Finding("secrets", "error", f, i, "high-confidence secret pattern")


@rule("public-leak", "error")
def _r_public(ctx):
    # Keyed on what the repository IS, not on how it was invoked. Gated on --org, this rule was off
    # during every `check --all` — that is, off for every sweep of the one repository in the
    # organisation that the whole world can read.
    if not (ctx["org_mode"] or ctx["facts"].get("archetype") == "org-profile"
            or ctx.get("private") is False):
        return
    for f in ctx["files"]:
        text = (ctx["path"] / f).read_text(errors="replace")
        for pat, why in P["internal_patterns"]:
            if "- \\[ \\]" in pat and "TEMPLATE" in f.upper():
                continue  # a template's boxes are the form, not a hardening backlog
            m = re.search(pat, text, re.M | re.I)
            if m:
                line = text[:m.start()].count("\n") + 1
                yield Finding("public-leak", "error", f, line,
                              f"{why} — this repo is world-readable")


@rule("broken-links", "error")
def _r_links(ctx):
    for f in ctx["files"]:
        base = (ctx["path"] / f).parent
        text = (ctx["path"] / f).read_text(errors="replace")
        for m in MD_LINK.finditer(text):
            t = m.group(1)
            if t.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if re.fullmatch(r"[…\.]{1,3}|\$\w+", t):
                continue        # an elision or placeholder quoted in prose, not a target
            target = (base / t.split("#")[0]).resolve()
            if not target.exists():
                yield Finding("broken-links", "error", f, text[:m.start()].count("\n") + 1,
                              f"link target missing: {t}")


@rule("fact-contradiction", "error")
def _r_contradiction(ctx):
    for key, (_, fn) in FACTS.items():
        try:
            _, claims = fn(ctx)
        except Exception:
            continue
        by_subject = {}
        for f, line, text, val, subj in claims:
            by_subject.setdefault(subj, {}).setdefault(
                json.dumps(val, sort_keys=True), []).append((f, line, text))
        for subj, values in by_subject.items():
            if len(values) < 2:
                continue
            label = f"{key}[{subj}]" if subj else key
            for val, where in sorted(values.items()):
                f, line, _ = where[0]
                yield Finding("fact-contradiction", "error", f, line,
                              f"{label}={val} here; {len(values)} incompatible values "
                              f"in this repo")


@rule("fact-vs-reality", "error", offline=False)
def _r_reality(ctx):
    for key, (offline, fn) in FACTS.items():
        try:
            authority, claims = fn(ctx)
        except Exception as exc:
            DEGRADED.append(f"fact {key!r}: {type(exc).__name__}")
            continue
        if authority is None:
            continue
        for f, line, text, val, _subj in claims:
            same = (val == authority) or (isinstance(val, dict) and isinstance(authority, dict)
                                          and all(authority.get(k) == v for k, v in val.items()))
            if not same:
                yield Finding("fact-vs-reality", "error", f, line,
                              f"{key}: doc says {val!r}, authority says {authority!r}")


@rule("claim-boxes", "warn", offline=False)
def _r_boxes(ctx):
    for f in ctx["files"]:
        if "TEMPLATE" in f.upper():
            continue  # a PR/issue template's boxes are the form, not open commitments
        p = ctx["path"] / f
        lines = p.read_text(errors="replace").splitlines()
        changed = False
        for i, line in enumerate(lines):
            if not re.match(r"\s*- \[[ x]\]", line):
                continue
            key = next((k for pat, k in rx(P["claim_boxes"]) if pat.search(line)), None)
            if key in SETTINGS and SETTINGS[key][2] == "public" and ctx.get("private"):
                key = None  # public-repo feature; unachievable here, so not verifiable
            if not key or key not in SETTINGS:
                if "- [ ]" in line:
                    yield Finding("claim-boxes", "warn", f, i + 1,
                                  "open commitment, not machine-verifiable")
                continue
            done = SETTINGS[key][0]("probe", ctx)
            marked = "[x]" in line.lower()
            if done is None:
                # We could not read the setting. Never rewrite a claim from a reading we did not make:
                # --fix editing a document to match a failed probe is a worse defect than a stale box.
                yield Finding("claim-boxes", "warn", f, i + 1,
                              f"{key}: could not read the setting — box left as it is")
                continue
            if done == marked:
                continue
            if ctx["fix"]:
                lines[i] = re.sub(r"\[[ xX]\]", "[x]" if done else "[ ]", line, count=1)
                changed = True
                yield Finding("claim-boxes", "warn", f, i + 1,
                              f"{key}: box now matches reality ({done})", True)
            else:
                yield Finding("claim-boxes", "warn", f, i + 1,
                              f"{key}: box says {marked}, reality is {done}")
        if changed:
            p.write_text("\n".join(lines) + "\n")


@rule("unfilled-contract", "error")
def _r_unfilled(ctx):
    """A scaffolded outline that shipped unfilled is worse than a missing file: it looks
    like documentation."""
    for f in ctx["files"]:
        for i, line in enumerate((ctx["path"] / f).read_text(errors="replace").splitlines(), 1):
            for m in re.finditer(r"\$SECTION_\w+|\$PLACEHOLDER", line):
                if any(a < m.start() and m.end() <= b for a, b in _code_spans(line)):
                    continue        # `$PLACEHOLDER` in backticks names the convention
                yield Finding("unfilled-contract", "error", f, i,
                              f"unfilled scaffold marker {m.group(0)}")
                break


@rule("phantom-command", "error")
def _r_phantom(ctx):
    """A documented command that does not exist is not merely unverified; it is false."""
    have = available_commands(ctx["path"])
    if not have:
        return                      # no recognisable runner in this repo; nothing to compare
    for cmd, (f, line, retired) in sorted(documented_commands(ctx["path"],
                                                              ctx["files"]).items()):
        runner = cmd.split()[0]
        if not any(h.startswith(runner) for h in have):
            continue                # that runner is not this repo's; ignore rather than guess
        if cmd in have or retired or is_history(f):
            continue                # retirement acknowledged, or dated history (exempt)
        yield Finding("phantom-command", "error", f, line,
                      f"`{cmd}` is documented but no such target or script exists")


@rule("unverified-command", "warn")
def _r_unverified(ctx):
    """'Never assert what you have not run.' A documented command no gate runs is an
    assertion nobody has tested."""
    have = available_commands(ctx["path"])
    gated = gated_commands(ctx["path"])
    if not have or not gated:
        return
    for cmd, (f, line, retired) in sorted(documented_commands(ctx["path"],
                                                              ctx["files"]).items()):
        if cmd in have and cmd not in gated and not retired:
            yield Finding("unverified-command", "warn", f, line,
                          f"`{cmd}` is documented but run by no gate — cover it or mark "
                          f"it untested where it appears")


@rule("adr-status", "warn")
def _r_adr(ctx):
    status = re.compile(r"^\s*[-*]?\s*(\*\*)?status(\*\*)?\s*[::]", re.I | re.M)
    for f in ctx["facts"]["adrs"]:
        text = (ctx["path"] / f).read_text(errors="replace")
        if not status.search(text):
            yield Finding("adr-status", "warn", f, None,
                          "no Status: field — cannot be superseded (MADR)")
        else:
            # The forward link may sit anywhere in the PARAGRAPH that declares the supersession.
            # Requiring it on the same line failed gestion's ADR-0002, which links forward to
            # ADR-0000 §AD-5 on the next line, because Markdown prose wraps.
            # Only a STATUS declaration counts. The word in ordinary prose — "an ADR
            # without a status cannot be superseded" — is a mention, not a status.
            lines = text.splitlines()

            def paragraph_at(i):
                out = []
                for ln in lines[i:]:
                    if not ln.strip():
                        break
                    out.append(ln)
                return " ".join(out)

            sup = [paragraph_at(i) for i, ln in enumerate(lines)
                   if re.match(r"\s*\**superseded\b", ln, re.I)
                   or re.match(r"\s*[-*]?\s*\**status\**\s*[::].*superseded", ln, re.I)]
            if sup and not any("](" in p for p in sup):
                yield Finding("adr-status", "warn", f, None,
                              "marked superseded but does not link forward")


@rule("readme-sections", "warn")
def _r_readme(ctx):
    have = " ".join(ctx["facts"]["readme_sections"])
    if not have:
        return
    for want, prompt in contract(ctx["facts"]["archetype"]):
        if want not in have:
            yield Finding("readme-sections", "warn", "README.md", None,
                          f"no section covering {want!r} — {prompt}")


# `orphan-reference` was deleted here. It flagged a governed doc that mentioned an app concept under
# `custom apps/` having no repository — but it derived that registry from `ROOT.glob("custom apps/*")`
# hardcoded in the ENGINE, which is a machine-local path and a decision in the one place ADR 0002 says
# a decision may never live. The drawer it read was retired by gestion #142, four of its seven folders
# are empty, and the rule's only firing across the org was a false positive: "Farmacia" in a Spanish
# list of clinic units (SOME, Dental, OIRS, Estadística-REM, Dirección) is a pharmacy. A registry of
# four empty human-named folders is worse than no registry, because it looks like one.


@rule("absolute-path", "warn")
def _r_abspath(ctx):
    for f in ctx["files"]:
        if is_history(f):
            continue
        heading = ""
        for i, line in enumerate((ctx["path"] / f).read_text(errors="replace").splitlines(), 1):
            if line.startswith("#"):
                heading = line
            m = ABSOLUTE_PATH.search(line)
            # A path named as off-limits is an identifier, not an instruction to use it. Making it
            # portable would destroy the warning it exists to give.
            if m and not (OFF_LIMITS.search(heading) or OFF_LIMITS.search(line)):
                yield Finding("absolute-path", "warn", f, i,
                              f"absolute host path {m.group(0)[:40]!r} — not portable")


@rule("personal-data", "warn")
def _r_pii(ctx):
    for f in ctx["files"]:
        if any(a in f for a in P["name_allow"]):
            continue
        for i, line in enumerate((ctx["path"] / f).read_text(errors="replace").splitlines(), 1):
            for e in EMAIL.findall(line):
                if not EMAIL_ALLOW.search(e):
                    yield Finding("personal-data", "warn", f, i, f"personal email {e}")
            for n in P["names"]:
                if n in line:
                    yield Finding("personal-data", "warn", f, i, f"real name {n!r} outside "
                                  f"{'/'.join(P['name_allow'])}")


@rule("doc-language", "warn")
def _r_lang(ctx):
    want = P.get("doc_language")
    lang = ctx["facts"]["doc_lang"]
    if not want or ctx["facts"]["archetype"] == "org-profile":
        return                      # the org profile is deliberately bilingual
    if lang not in (want, "n/a"):
        yield Finding("doc-language", "warn", None, None,
                      f"repo docs are {lang}; this owner's policy is {want!r}")


@rule("nested-repo", "info")
def _r_nested(ctx):
    for n in ctx["facts"]["nested"]:
        yield Finding("nested-repo", "info", n, None,
                      "git repo inside this working tree with no .gitmodules")


@rule("branch-name", "info", offline=False)
def _r_branch(ctx):
    b = ctx["facts"]["default_branch"]
    if b and b != "main":
        yield Finding("branch-name", "info", None, None,
                      f"default branch is {b!r}; every other repo uses 'main'")


RATIONALE = {
    "missing-required": "Community-standard files absent; 5 repos lack CONTRIBUTING today.",
    "tracked-not-present": "A tracked file the tree lacks used to kill the run with a traceback.",
    "license-posture": "ADR 0010: AGPL-3.0-or-later org-wide, inherited from what the apps link.",
    "canon-drift": "Mechanical files have one correct form; drift is a bug, not a variant.",
    "canon-stamp": "A vendored copy has no canon/ to compare against; it carries the digest instead.",
    "secrets": "gestion/.githooks/pre-commit already chose this posture; propagate it.",
    "public-leak": "The org .github repo is world-readable; the repos it serves are not.",
    "broken-links": "Offline check so CI stays deterministic; moved files break relative links.",
    "fact-contradiction": "Four sources in gestion disagree about team size.",
    "fact-vs-reality": "A claim a machine can check must match the machine.",
    "claim-boxes": "Unchecked boxes are a backlog hiding in a document.",
    "adr-status": "22+ ADRs, zero Status fields — nothing can be superseded.",
    "unfilled-contract": "A shipped outline looks like documentation and is not.",
    "licence-declaration": "Apps declare a licence in appinfo, composer and package at once.",
    "licence-inventory": "The notices document must match what is actually installed.",
    "licence-prose": "SKILL.md and the public profile still called the org proprietary after 0010.",
    "phantom-command": "A documented command with no target is a lie, not a gap.",
    "unverified-command": "8 of gestion's 14 documented make commands are run by no gate.",
    "readme-sections": "Presence, never order; archetype decides the extras.",
    "absolute-path": "AGENTS.md:32 hardcodes /srv/syncthing/CESFAMS.",
    "personal-data": "Names and personal addresses belong in CONTRIBUTORS/LICENSE only.",
    "doc-language": "Repo docs English; only the org profile is bilingual.",
    "nested-repo": "epidemiologia sits inside gestion/apps with no .gitmodules.",
    "branch-name": "Every repo is on main; another default is a drift signal.",
}


# ---------------------------------------------------------------- settings

@setting("dependabot-security-updates")
def _s_dependabot_fixes(action, ctx):
    """Separate from alerts, and easy to conflate with them: alerts tell you, updates open the PR.
    gestion's checklist asked for both on one line while alerts were on and updates were off, so the
    line could not be honestly ticked either way."""
    repo = ctx["facts"]["repo"]
    if action == "probe":
        got = gh("api", f"repos/{ORG}/{repo}/automated-security-fixes")
        if not isinstance(got, dict) or "enabled" not in got:
            return None                     # gh() already recorded the failure
        return got["enabled"] is True
    return sh(["gh", "api", "-X", "PUT",
               f"repos/{ORG}/{repo}/automated-security-fixes"])[0] == 0


@setting("dependabot-alerts")
def _s_dependabot(action, ctx):
    repo = ctx["facts"]["repo"]
    if action == "probe":
        # 204 = on, 404 = off, anything else = we could not tell. `code == 0` collapsed the third case
        # into "off", and because --fix rewrites a checkbox to match the probe, one failed call
        # silently edited SECURITY.md to claim a security feature was disabled while it was on.
        _, out, _ = sh(["gh", "api", "-i", f"repos/{ORG}/{repo}/vulnerability-alerts"])
        m = re.search(r"HTTP/[\d.]+ (\d{3})", out or "")
        status = int(m.group(1)) if m else None
        if status in (204, 200):
            return True
        if status == 404:
            return False
        DEGRADED.append(f"setting 'dependabot-alerts': unreadable (status {status})")
        return None
    return sh(["gh", "api", "-X", "PUT", f"repos/{ORG}/{repo}/vulnerability-alerts"])[0] == 0


@setting("private-vuln-reporting", scope="public")
def _s_pvr(action, ctx):
    repo = ctx["facts"]["repo"]
    path = f"repos/{ORG}/{repo}/private-vulnerability-reporting"
    if action == "probe":
        return sh(["gh", "api", path])[0] == 0
    return sh(["gh", "api", "-X", "PUT", path])[0] == 0


@setting("secret-scanning", scope="public")
def _s_scanning(action, ctx):
    repo = ctx["facts"]["repo"]
    if action == "probe":
        got = gh("api", f"repos/{ORG}/{repo}",
                 "--jq", ".security_and_analysis.secret_scanning.status")
        return got == "enabled"
    return sh(["gh", "api", "-X", "PATCH", f"repos/{ORG}/{repo}", "-f",
               "security_and_analysis[secret_scanning][status]=enabled"])[0] == 0


def _guard_2fa():
    """Non-negotiable pre-flight. Enforcing 2FA removes members who lack it — and the only member is
    the owner.

    It fails CLOSED, and that is the whole point. `gh()` returns None when the call fails, so
    `str(out or "")` read a request that never reached GitHub as "nobody lacks 2FA" and would have
    gone on to enforce it. Losing control of the organisation is not an acceptable outcome of a flaky
    network. Asserted in `selftest`, as ADR 0003 requires."""
    out = gh("api", f"orgs/{ORG}/members?filter=2fa_disabled", "--jq", ".[].login")
    if out is None:
        return ["<could not read the 2FA-disabled member list — refusing to enforce>"]
    return [m for m in str(out).split("\n") if m]


@setting("org-2fa", guard=_guard_2fa)
def _s_2fa(action, ctx):
    if action == "probe":
        return gh("api", f"orgs/{ORG}", "--jq", ".two_factor_requirement_enabled") is True
    return sh(["gh", "api", "-X", "PATCH", f"orgs/{ORG}",
               "-F", "two_factor_requirement_enabled=true"])[0] == 0


def settings_report(repo: Path, apply: bool) -> int:
    facts = scan(repo)
    ctx = {"facts": facts, "path": repo}
    private = gh("api", f"repos/{ORG}/{facts['repo']}", "--jq", ".private") is True
    rc = 0
    for key, (fn, guard, scope) in SETTINGS.items():
        if scope == "public" and private:
            print(f"n/a  {key}  — public-repo feature; this repo is private")
            continue
        state = fn("probe", ctx)
        print(f"{'on ' if state else 'OFF'}  {key}")
        if not apply or state:
            continue
        if guard:
            blocked = guard()
            if blocked:
                print(f"       REFUSED — members without 2FA: {', '.join(blocked)}")
                print("       Order is forced: enrol those accounts first, then enforce "
                      "org-wide, or you lock yourself out.")
                rc = 1
                continue
        print(f"       applying… {'ok' if fn('apply', ctx) else 'FAILED'}")
    return rc


# ---------------------------------------------------------------- check

def check(repo: Path, level="full", org_mode=False, offline=False, fix=False,
          explain=False, collected=None) -> int:
    facts = scan(repo)
    ctx = {"path": repo, "facts": facts, "files": facts["governed"], "level": level,
           "org_mode": org_mode, "fix": fix, "known_repos": list(discover()["repos"]),
           "private": None if offline else
                      gh("api", f"repos/{ORG}/{facts['repo']}", "--jq", ".private") is True}
    errors = 0
    collected = [] if collected is None else collected
    print(f"\n== {facts['repo']}  [{facts['archetype']}, {facts['branch']}, "
          f"{facts['license_kind']}]  {len(ctx['files'])} governed docs")
    for name, severity, is_offline, fn in CHECKS:
        if offline and not is_offline:
            # A skipped rule knows nothing. Recording it as degraded stops the baseline diff calling
            # its findings "resolved" — which it did, reporting a non-`main` default
            # branch as fixed in the same run that printed SKIP for the rule that finds it.
            print(f"SKIP    {name:<20} needs org-scoped auth (--offline)")
            DEGRADED.append(f"rule {name!r}: skipped (--offline)")
            SKIPPED_RULES.add(name)
            continue
        try:
            found = list(fn(ctx))
        except Exception as e:  # a broken rule must not mask the others
            print(f"RULEERR {name:<20} {type(e).__name__}: {e}")
            continue
        for f in found:
            print(f)
            collected.append(f)
            if f.severity == "error" and not f.fixed:
                errors += 1
        if found and explain:
            print(f"        why: {RATIONALE.get(name, '-')}")
    print(f"-- {errors} error(s)")
    return 1 if errors else 0


BASELINE = SKILL / "baseline.json"


def fingerprint(f: Finding) -> str:
    """Line numbers move when a paragraph is edited; the defect is the same defect.
    Identity is rule + file + message, never position."""
    return f"{f.rule}|{f.file or '-'}|{f.msg}"


def baseline_diff(current: dict, save: bool) -> int:
    """Improvement is only observable against what was true last time."""
    old = json.loads(BASELINE.read_text()) if BASELINE.exists() else {}
    new_by_rule = {}
    total_new = total_gone = 0
    for repo, fps in sorted(current.items()):
        was, now = set(old.get(repo, [])), set(fps)
        added, absent = sorted(now - was), sorted(was - now)
        # A finding from a rule that did not run has not been resolved; nobody looked.
        unknown = [fp for fp in absent if fp.split("|")[0] in SKIPPED_RULES]
        gone = [fp for fp in absent if fp.split("|")[0] not in SKIPPED_RULES]
        total_new += len(added)
        total_gone += len(gone)
        if not old:
            print(f"  {repo:<16} {len(now)} findings recorded (first baseline)")
            continue
        tail = f"  ?{len(unknown)} unknown" if unknown else ""
        print(f"  {repo:<16} +{len(added)} new  -{len(gone)} resolved  ={len(now & was)} open{tail}")
        for fp in added[:6]:
            print(f"      NEW      {fp}")
            new_by_rule.setdefault(fp.split('|')[0], set()).add(repo)
        for fp in gone[:6]:
            print(f"      RESOLVED {fp}")
        for fp in unknown[:6]:
            print(f"      UNKNOWN  {fp}  (its rule did not run)")
    # The loop above walks `current`, so a repository that has left the audit produces no line at
    # all: its findings simply sit in the file being neither new, resolved nor open. `common` rotted
    # there after the repository was deleted from GitHub, and only a hand-read of the JSON found it.
    for repo in sorted(set(old) - set(current)):
        print(f"  STALE {repo} (recorded, no clone discovered)")
    # A rule appearing across most repos at once is a rule change; documentation does not
    # rot in lockstep. Requiring ALL of them was too strict — one already-compliant repo
    # (repo-docs itself) was enough to silence the warning.
    for rulename, repos in sorted(new_by_rule.items()):
        if len(repos) >= 2 and len(repos) >= len(current) / 2:
            print(f"\n  ! {rulename!r} is new in {len(repos)} of {len(current)} repos "
                  f"— suspect the rule or a canon change, not the documentation")
    if DEGRADED:
        print(f"\n  ! degraded run — {len(set(DEGRADED))} probe(s) could not be evaluated, so what "
              f"they check is missing from these counts, not passing:")
        for d in sorted(set(DEGRADED))[:8]:
            print(f"      {d}")
    if save and DEGRADED:
        print("\n  baseline NOT saved: recording a degraded run would retire every finding it "
              "failed to evaluate. Re-run once the probes succeed.")
        return 1
    if save:
        BASELINE.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n")
        print(f"\n  baseline saved: {sum(len(v) for v in current.values())} findings "
              f"across {len(current)} repos")
    elif old:
        print(f"\n  net: +{total_new} / -{total_gone}   (--save-baseline to record)")
    return 0


def audit_prompt(repo: Path) -> str:
    """On-demand model read. Findings that recur get promoted to a @fact or @rule."""
    facts = scan(repo)
    return (f"Read every file below in {repo} and report contradictions, stale claims, "
            f"deprecated references and weird references that a regex cannot express. "
            f"Report as: file:line — claim — why it is wrong. Do not fix anything.\n\n"
            + "\n".join(facts["governed"]))


# ---------------------------------------------------------------- selftest

def _porcelain_path(line: str) -> str:
    """sh() strips stdout, so ' M file' may arrive as 'M file'. Split on whitespace —
    slicing a fixed column silently truncates the filename."""
    parts = line.split(None, 1)
    return (parts[1] if len(parts) > 1 else parts[0]).strip().strip('"')


def open_pr(repo: Path, paths: list, level: str) -> str:
    """Branch, commit only `paths`, push, open a DRAFT PR.
    Refuses on a dirty tree — a docs run must never sweep up unrelated work in progress.
    Never force-pushes, never merges, never touches the default branch."""
    facts = scan(repo)
    _, dirty, _ = sh(["git", "-C", str(repo), "status", "--porcelain"])
    stray = [ln for ln in dirty.split("\n") if ln and _porcelain_path(ln) not in paths]
    if stray:
        return ("refused: working tree has unrelated changes —\n  "
                + "\n  ".join(stray[:8]) + "\ncommit or stash them first")
    if not paths:
        return "nothing to open a PR for"
    n = 1
    _, existing, _ = sh(["git", "-C", str(repo), "branch", "--list", f"docs/{level}-*"])
    while f"docs/{level}-{n}" in existing:
        n += 1
    branch = f"docs/{level}-{n}"
    for argv in (["git", "-C", str(repo), "checkout", "-q", "-b", branch],
                 ["git", "-C", str(repo), "add", "--", *paths],
                 ["git", "-C", str(repo), "commit", "-qm",
                  f"docs: {level} pass on {facts['repo']}\n\n"
                  f"Generated by repo-docs; prose reviewed before merge."],
                 ["git", "-C", str(repo), "push", "-q", "-u", "origin", branch]):
        code, _, err = sh(argv)
        if code != 0:
            return f"failed at {argv[3] if len(argv) > 3 else argv[0]}: {err[:200]}"
    code, out, err = sh(["gh", "pr", "create", "--draft", "--repo", f"{ORG}/{facts['repo']}",
                         "--head", branch, "--base", facts.get("default_branch") or "main",
                         "--title", f"docs: {level} pass",
                         "--body", "Documentation pass from `repo-docs`. Draft: prose needs a "
                                   "human read before merge.\n\nRun `docs.py check <repo> "
                                   "--explain` to see what remains."])
    return out if code == 0 else f"branch pushed, PR not created: {err[:200]}"


def selftest() -> None:
    global ROOT, gh, CANON_DIR

    # `SELF_REF` carried the organisation name as a backslash-escaped template placeholder.
    # `string.Template`'s escape for a literal dollar is a doubled dollar, not a backslash, so `render`
    # left the backslash in place and every vendored copy read a leading backslash-A — the
    # start-of-string anchor, so the alternative could never match. The naive repair renders to a bare
    # `APS-Conecta`, which also matches every `github.com/APS-Conecta/<repo>` URL in our own
    # documentation. Both directions are asserted, and the pattern now holds no placeholder at all, so
    # it reads identically in canon and in every copy.
    assert SELF_REF.search("APS-Conecta's own code is proprietary."), \
        "the hyphenated organisation name must self-refer"
    assert not SELF_REF.search("https://github.com/APS-Conecta/gestion/blob/main/LICENSE"), \
        "a repository URL names a location, not the subject of a sentence"

    # This file is rendered into every repository -- `canon/repo-docs.py` is a symlink to it -- so
    # ANYTHING in it that looks like a template variable is substituted on the way out. `SELF_REF`
    # was one such leak (#6); `harvest`'s substitution table was the other (#7), and it held the very
    # four names `render` supplies, so every vendored copy carried the owner's real name where the
    # table should say `$` followed by `holder`. Rather than assert those four, assert the
    # invariant that makes the class impossible: rendering this file must change nothing in it,
    # comments included. `$SECTION_` and `$PLACEHOLDER` survive because they are not variables
    # `render` supplies; anything that IS one fails here on the day it is written.
    _vars = dict.fromkeys(canon_vars({}), "X")   # every name render supplies, never a hand copy
    _self = Path(__file__).read_text()
    assert string.Template(_self).safe_substitute(_vars) == _self, \
        "this file is rendered into every repository, so nothing in it may be a live placeholder"

    # ADR 0003 says the org-2FA pre-flight "is asserted in the selftest and must never become
    # advisory". It said so while nothing asserted it. Enforcing 2FA removes every member who lacks
    # it, and this organisation has exactly one member, so a guard that fails OPEN when it cannot
    # reach GitHub can lock the owner out of everything.
    _real_gh = gh
    try:
        gh = lambda *a, **k: None                    # noqa: E731 — simulate a failed API call
        assert _guard_2fa(), "org-2fa pre-flight must BLOCK when it cannot read the member list"
        gh = lambda *a, **k: ""                      # noqa: E731 — reachable, nobody lacks 2FA
        assert _guard_2fa() == [], "empty member list must not block"
    finally:
        gh = _real_gh

    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "with space"
        repo = base / "demo"
        (repo / "docs" / "adr").mkdir(parents=True)
        sh(["git", "init", "-q", "-b", "main", str(repo)])
        sh(["git", "-C", str(repo), "remote", "add", "origin",
            f"https://github.com/{ORG}/demo.git"])
        (repo / "README.md").write_text(
            "# demo\n\n## What this is\n\n## Status\n\n## Quickstart\n\n## Licence\n"
            "See [missing](docs/nope.md) and /srv/syncthing/CESFAMS.\n"
            "A three-person team works here.\n"
            "APS Conecta's own code is proprietary.\n"
            "The logo and lockup stay all rights reserved under AGPL 7(e).\n"
            "Never describe our own code as proprietary.\n")
        (repo / "docs" / "OFFLIMITS.md").write_text(
            "# demo docs\n\n## Do not touch\n\n`/srv/syncthing/OTHER` is another tenant's.\n")
        (repo / "CONTRIBUTING.md").write_text("A single developer works here.\n")
        (repo / "LICENSE").write_text("MIT License\nCopyright (c) 2026\n")
        (repo / "docs" / "adr" / "0001-x.md").write_text("# x\n\nNo status field here.\n")
        sh(["git", "-C", str(repo), "add", "-A"])
        sh(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
            "commit", "-qm", "init"])

        # nested repo must halt the walk
        nested = repo / "apps" / "inner"
        nested.mkdir(parents=True)
        sh(["git", "init", "-q", str(nested)])
        (nested / "README.md").write_text("# inner\n")

        old_root, ROOT = ROOT, base
        try:
            facts = scan(repo)
            assert facts["repo"] == "demo", facts["repo"]          # identity from remote
            assert facts["license_kind"] == "mit", facts["license_kind"]
            assert "apps/inner" in facts["nested"], facts["nested"]
            assert not any(f.startswith("apps/inner") for f in facts["governed"])

            ctx = {"path": repo, "facts": facts, "files": facts["governed"], "level": "full",
                   "org_mode": False, "fix": False, "known_repos": ["demo"]}

            assert any(f.rule == "license-posture" for f in _r_licence(ctx))
            assert any("nope.md" in f.msg for f in _r_links(ctx))
            assert any(f.rule == "absolute-path" for f in _r_abspath(ctx))
            assert "docs/OFFLIMITS.md" in facts["governed"]      # or the next assert is vacuous
            assert not any(f.file == "docs/OFFLIMITS.md" for f in _r_abspath(ctx)), \
                "a path named as off-limits is an identifier, not a portability defect"

            # One claim, not three: the marks carve-out is correct and a prohibition is not a claim.
            prose = list(_r_licence_prose(ctx))
            assert [f.rule for f in prose] == ["licence-prose"], [f.msg for f in prose]
            assert "proprietary" in prose[0].msg

            # The default branch is not the checked-out one, or a feature branch bakes its own name
            # into docs.yml and opens pull requests against itself.
            sh(["git", "-C", str(repo), "update-ref", "refs/remotes/origin/main", "HEAD"])
            sh(["git", "-C", str(repo), "checkout", "-q", "-b", "feature/x"])
            assert default_branch(repo) == "main", default_branch(repo)
            assert canon_vars(scan(repo))["branch"] == "main"
            sh(["git", "-C", str(repo), "checkout", "-q", "main"])
            assert any(f.rule == "adr-status" for f in _r_adr(ctx))
            assert any(f.rule == "fact-contradiction" for f in _r_contradiction(ctx)), \
                "three-person vs single developer must contradict"
            # CODEOWNERS, not SECURITY.md: GitHub cannot default CODEOWNERS, so it is always a gap when
            # absent, whereas SECURITY.md is legitimately inherited from the org and must NOT be.
            g = gaps(facts, "full", False)
            assert "CODEOWNERS" in g, g
            assert "SECURITY.md" not in g, "an org-inheritable file must not be reported as missing"

            # A hook without its executable bit is inert in every clone, and git records the bit
            # (100755 vs 100644). --fix wrote the text only, so 5 of 6 repos carried a dead
            # secret-guard while CONTRIBUTING.md documented it as a gate.
            hook = repo / ".githooks" / "pre-commit"
            hook.parent.mkdir(parents=True, exist_ok=True)
            hook.write_text(render("pre-commit", canon_vars(facts)))
            hook.chmod(0o644)
            assert any("NOT EXECUTABLE" in f.msg for f in _r_canon(dict(ctx, fix=False))), \
                "a present-but-inert hook must be reported as drift"
            list(_r_canon(dict(ctx, fix=True)))
            assert os.access(hook, os.X_OK), "--fix must set the executable bit"

            # A vendored copy has no canon/ to diff against (ADR 0004), so it carries canon's digest
            # instead. Blanking the stamp line before hashing is what lets that converge — the stamp
            # is written into a canon source, so a digest that counted it would move every time it
            # was written. Asserted both ways: a digest that ignored everything would pass the first
            # of these on its own.
            assert _canon_digest({"x": 'CANON_STAMP = ""\nbody\n'}) == \
                   _canon_digest({"x": 'CANON_STAMP = "0123456789ab"\nbody\n'}), \
                "the digest must not depend on the stamp it writes"
            assert _canon_digest({"x": 'CANON_STAMP = ""\nbody\n'}) != \
                   _canon_digest({"x": 'CANON_STAMP = ""\nbodz\n'}), \
                "...but every other byte must still count"

            vendored = repo / P["canon"]["repo-docs.py"]
            vendored.parent.mkdir(parents=True, exist_ok=True)
            vendored.write_text(render("repo-docs.py", canon_vars(facts)))
            assert not list(_r_canon_stamp(ctx)), "a freshly rendered copy carries today's stamp"

            # Seed the violation rather than watch it pass: move canon, and every copy already
            # rendered is one engine behind. Against a throwaway copy, so real canon is never edited.
            fake = Path(td) / "canon"
            shutil.copytree(CANON_DIR, fake)
            old_canon, CANON_DIR = CANON_DIR, fake
            try:
                (fake / "CODEOWNERS").write_text((fake / "CODEOWNERS").read_text() + "# seeded\n")
                stale = list(_r_canon_stamp(ctx))
                assert [f.severity for f in stale] == ["warn"], [str(f) for f in stale]
                assert "canon is now" in stale[0].msg, stale[0].msg
            finally:
                CANON_DIR = old_canon

            before = sorted(p.name for p in repo.rglob("*"))
            scaffold(repo, "full", False, write=False)
            assert sorted(p.name for p in repo.rglob("*")) == before, "dry run wrote files"

            original = (repo / "README.md").read_text()
            scaffold(repo, "lite", False, write=True)
            assert (repo / "README.md").read_text() == original, "overwrote an existing file"

            # a docs PR must never sweep up unrelated work in progress
            (repo / "CONTRIBUTING.md").write_text("edited, unrelated\n")  # tracked+modified
            (repo / "unrelated.txt").write_text("work in progress\n")
            out = open_pr(repo, ["README.md"], "full")
            assert out.startswith("refused:"), out
            assert "unrelated.txt" in out, out
            assert "CONTRIBUTING.md" in out, out  # porcelain column must not truncate

            # An exemplar with no remote yields, for its name, a pattern that is two bare word
            # boundaries: it matches between every word and would splice the repo placeholder
            # into every byte of every canon file. Refused before canon is touched.
            try:
                harvest(Path(td) / "nowhere")
                raise AssertionError("harvest must refuse an exemplar it cannot name")
            except SystemExit as exc:
                assert "cannot name" in str(exc), exc
        finally:
            ROOT = old_root
    print("selftest: ok")


# ---------------------------------------------------------------- cli

def main(argv=None):
    p = argparse.ArgumentParser(prog="docs.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, **kw):
        s = sub.add_parser(name, **kw)
        return s

    add("discover").add_argument("--clone", action="store_true")
    add("scan").add_argument("repo")
    c = add("check")
    c.add_argument("repo", nargs="?")
    c.add_argument("--all", action="store_true")
    c.add_argument("--level", default="full", choices=sorted(P["levels"]))
    c.add_argument("--org", dest="org_mode", action="store_true")
    c.add_argument("--offline", action="store_true")
    c.add_argument("--fix", action="store_true")
    c.add_argument("--explain", action="store_true")
    c.add_argument("--save-baseline", dest="save_baseline", action="store_true")
    add("audit").add_argument("repo")
    add("outline").add_argument("repo")
    add("licences").add_argument("repo")
    add("harvest").add_argument("exemplar", nargs="?", default=str(ROOT / "gestion"))
    s = add("scaffold")
    s.add_argument("repo")
    s.add_argument("--level", default="full", choices=sorted(P["levels"]))
    s.add_argument("--org", dest="org_mode", action="store_true")
    s.add_argument("--write", action="store_true")
    st = add("settings")
    st.add_argument("repo")
    st.add_argument("--apply-settings", dest="apply", action="store_true")
    pr = add("pr")
    pr.add_argument("repo")
    pr.add_argument("--level", default="full", choices=sorted(P["levels"]))
    add("selftest")
    a = p.parse_args(argv)

    if a.cmd == "discover":
        d = discover()
        print(json.dumps(d, indent=2))
        if d["unreadable"]:
            print("\nunreadable (a .git we could not name — NOT the same as absent):")
            for u in d["unreadable"]:
                print(f"  {u}")
        miss = missing_clones()
        if miss:
            print(f"\nnot cloned: {', '.join(miss)}")
            for m in miss if a.clone else []:
                print(f"cloning {m}…",
                      sh(["gh", "repo", "clone", f"{ORG}/{m}", str(ROOT / m)])[0] == 0)
        return 0

    if a.cmd == "selftest":
        selftest()
        return 0
    if a.cmd == "harvest":
        print("\n".join(harvest(Path(a.exemplar))) or "(nothing harvested)")
        return 0
    if a.cmd == "scan":
        print(json.dumps(scan(resolve(a.repo)), indent=2))
        return 0
    if a.cmd == "outline":
        repo = resolve(a.repo)
        f = scan(repo)
        print(f"README contract for {f['repo']} (archetype: {f['archetype']})\n")
        for k, prompt in contract(f["archetype"]):
            mark = "ok " if k in " ".join(f["readme_sections"]) else "MISSING"
            print(f"  {mark:8} {k:<11} {prompt}")
        return 0
    if a.cmd == "licences":
        repo = resolve(a.repo)
        print("declared by this repo:")
        for where, kind in sorted(licence_sites(repo).items()):
            print(f"  {kind or '?':<12} {where}")
        inv = inventory(repo)
        fams = {}
        for comp, lic, src, phase in inv:
            fams.setdefault(f"{lic or 'unknown'} ({phase})", []).append(comp)
        print(f"\nthird-party ({len(inv)} components):")
        for fam, comps in sorted(fams.items(), key=lambda kv: -len(kv[1])):
            print(f"  {fam:<12} {len(comps):>3}  {', '.join(sorted(comps)[:4])}"
                  f"{' …' if len(comps) > 4 else ''}")
        return 0
    if a.cmd == "audit":
        print(audit_prompt(resolve(a.repo)))
        return 0
    if a.cmd == "scaffold":
        out = scaffold(resolve(a.repo), a.level, a.org_mode, a.write)
        print("\n".join(f"{'wrote' if a.write else 'would write'}  {o}" for o in out)
              or "(no gaps)")
        return 0
    if a.cmd == "settings":
        return settings_report(resolve(a.repo), a.apply)
    if a.cmd == "pr":
        repo = resolve(a.repo)
        _, changed, _ = sh(["git", "-C", str(repo), "status", "--porcelain"])
        all_paths = [_porcelain_path(ln) for ln in changed.split("\n") if ln]
        # only documentation may ride a docs PR; anything else is unrelated work in progress
        docs_paths = [p for p in all_paths if p.endswith((".md", "LICENSE", "CODEOWNERS"))
                      or p.startswith((".github/", ".githooks/", "docs/"))]
        print(open_pr(repo, docs_paths, a.level))
        return 0
    if a.cmd == "check":
        if a.offline and a.save_baseline:
            # CI runs --offline and evaluates a subset. Recording that subset would retire every
            # finding only the authenticated rules can see.
            sys.exit("repo-docs: --offline cannot save a baseline — it evaluates a subset "
                     "of the rules, so recording it would retire what it never ran")
        targets = ([Path(v) for v in discover()["repos"].values()] if a.all
                   else [resolve(a.repo)])
        rc, snapshot = 0, {}
        for t in targets:
            found = []
            rc = max(rc, check(t, a.level, a.org_mode, a.offline, a.fix, a.explain, found))
            snapshot[repo_name(t)[1] or t.name] = sorted({fingerprint(f) for f in found
                                                          if not f.fixed})
        if a.all or a.save_baseline:
            print("\n== baseline")
            baseline_diff(snapshot, a.save_baseline)
        return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
