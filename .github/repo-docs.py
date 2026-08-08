#!/usr/bin/env python3
"""repo-docs — documentation control for APS-Conecta.

Audit first, scaffold second. Everything extensible is a table:
profiles/*.json for policy; CHECKS, FACTS, SETTINGS for rules.
If tuning needs a function body edited, the seam is wrong.

Stdlib only. Every subprocess call takes an argv list — paths contain spaces.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import string
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
CANON_DIR = SKILL / "canon"
PUBLIC_DIR = SKILL / "public"
PROFILES = SKILL / "profiles"

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

CHECKS: list = []
FACTS: dict = {}
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
    p = subprocess.run(argv, cwd=str(cwd) if cwd else None,
                       capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def gh(*args):
    """gh api wrapper. Returns parsed JSON, raw text, or None when the call fails."""
    code, out, _ = sh(["gh", *args])
    if code != 0:
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
    found, nested, unmanaged = {}, {}, {}
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
            "unmanaged": dict(sorted(seen.items(), key=lambda kv: -kv[1]))}


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
    return [r for r in rel if not (repo / r.split("/")[0] / ".git").exists()]


def governed(repo: Path) -> list:
    return tracked_md(repo)


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
    for extra in ("docs/index.md", ".githooks/pre-commit", ".github/workflows/docs.yml", "docs/adr"):
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
    for f in files:
        for _, text in HEADING.findall((repo / f).read_text(errors="replace")):
            words = re.findall(r"[a-záéíóúñ]+", text.lower())
            if any(w in set(P["es_stopwords"]) for w in words):
                es += 1
            elif words:
                en += 1
    if not (es or en):
        return "n/a"
    return "es" if es > en else ("mixed" if es else "en")


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
        "stacks": stacks, "archetype": archetype(repo, stacks, name),
        "license_kind": license_kind(repo), "health": find_health(repo),
        "governed": files, "docs": sorted(f for f in files if f.startswith("docs/")),
        "adrs": sorted(f for f in files if "/adr/" in f or f.startswith("adr/")),
        "readme_sections": sections, "nested": sorted(set(nested)),
        "doc_lang": doc_lang(repo, files),
        "has_ci": (repo / ".github" / "workflows").is_dir(),
    }


# ---------------------------------------------------------------- canon

def canon_vars(facts: dict) -> dict:
    return {"org": ORG, "repo": facts.get("repo") or "", "branch": facts.get("branch") or "main",
            "holder": HOLDER, "year": "2026"}


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
    """Unknown $var survives verbatim so it stays visible as unfilled."""
    src = (CANON_DIR / name).read_text()
    return string.Template(src).safe_substitute(vars_)


def harvest(exemplar: Path) -> list:
    """Refresh canon/ from the exemplar. One convention, one home."""
    written = []
    org, name = repo_name(exemplar)
    subs = [(re.escape(HOLDER), "Daniel Espinoza Charrier"), (rf"\b{re.escape(name or '')}\b", "repo-docs"),
            (re.escape(ORG), "APS-Conecta"), (r"\b2026\b", "2026")]
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


def required(level: str, org_mode: bool) -> tuple:
    return P["org_level"] if org_mode else P["levels"][level]


def gaps(facts: dict, level: str, org_mode: bool) -> list:
    have = set(facts["health"])
    return [r for r in required(level, org_mode) if r not in have]


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
                title = Path(missing).stem.replace("-", " ").replace("_", " ").title()
                dest.write_text(f"# {title}\n\n$PLACEHOLDER — authored, never templated.\n")
    if org_mode and write:
        for name in ("CONTRIBUTING.md", "SECURITY.md"):
            src = PUBLIC_DIR / name
            dst = repo / name
            if src.exists() and not dst.exists():
                dst.write_text(string.Template(src.read_text()).safe_substitute(vars_))
    return out


# ---------------------------------------------------------------- facts

def _claims(repo: Path, files: list, pattern: re.Pattern, norm, subj=None):
    """subj groups claims that are about different things — 'Nextcloud 34' and
    'Redis 8' are complementary, not contradictory."""
    out = []
    for f in files:
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


@rule("licence-copyleft", "warn")
def _r_copyleft(ctx):
    """Copyleft under a proprietary product is a question for a human, not a regex:
    running alongside AGPL software is fine, linking it into proprietary code is not."""
    if P.get("licence_posture") != "proprietary":
        return
    hits = {}
    for comp, lic, src, phase in inventory(ctx["path"]):
        if phase != "runtime":
            continue
        if lic in (P.get("copyleft") or []):
            hits.setdefault(lic, []).append(comp)
    for lic, comps in sorted(hits.items()):
        yield Finding("licence-copyleft", "warn", None, None,
                      f"{len(comps)} {lic} dependencies in a proprietary product "
                      f"(e.g. {', '.join(comps[:3])}) — confirm arm's length, not linked")


@rule("canon-drift", "error")
def _r_canon(ctx):
    vars_ = canon_vars(ctx["facts"])
    for canon_rel, repo_rel in P["canon"].items():
        dst, src = ctx["path"] / repo_rel, CANON_DIR / canon_rel
        if canon_rel in P["canon_seed_only"] or not src.exists():
            continue
        if not dst.exists():
            # Absence is drift too. A directory requirement is satisfied by its canon
            # members, never by the directory existing with one file in it.
            if ctx["fix"]:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(render(canon_rel, canon_vars(ctx["facts"])))
                yield Finding("canon-drift", "error", repo_rel, None, "added from canon/", True)
            else:
                yield Finding("canon-drift", "error", repo_rel, None,
                              f"missing; canon/{canon_rel} defines it")
            continue
        want = render(canon_rel, vars_)
        if dst.read_text(errors="replace") == want:
            continue
        if ctx["fix"]:
            dst.write_text(want)
            yield Finding("canon-drift", "error", repo_rel, None, "restored from canon/", True)
        else:
            yield Finding("canon-drift", "error", repo_rel, None,
                          f"differs from canon/{canon_rel} — --fix restores it")


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
    if not ctx["org_mode"]:
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
        except Exception:
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
            # a forward link may sit anywhere on the line that says "superseded"
            # Only a STATUS declaration counts. The word in ordinary prose — "an ADR
            # without a status cannot be superseded" — is a mention, not a status.
            sup = [ln for ln in text.splitlines()
                   if re.match(r"\s*\**superseded\b", ln, re.I)
                   or re.match(r"\s*[-*]?\s*\**status\**\s*[::].*superseded", ln, re.I)]
            if sup and not any("](" in ln for ln in sup):
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


@rule("orphan-reference", "warn")
def _r_orphan(ctx):
    def norm(x):
        import unicodedata
        x = unicodedata.normalize("NFKD", x.strip().lower())
        return "".join(c for c in x if not unicodedata.combining(c)).replace(" ", "-")
    known = {norm(k) for k in ctx["known_repos"]}
    local = {p.name for p in ROOT.glob("custom apps/*") if p.is_dir()}
    orphans = {n for n in local if norm(n) not in known}
    for f in ctx["files"]:
        text = (ctx["path"] / f).read_text(errors="replace")
        for name in orphans:
            m = re.search(rf"\b{re.escape(name.strip())}\b", text)
            if m:
                yield Finding("orphan-reference", "warn", f, text[:m.start()].count("\n") + 1,
                              f"mentions {name.strip()!r} — no such repo in {ORG}")


@rule("absolute-path", "warn")
def _r_abspath(ctx):
    for f in ctx["files"]:
        for i, line in enumerate((ctx["path"] / f).read_text(errors="replace").splitlines(), 1):
            m = ABSOLUTE_PATH.search(line)
            if m and not is_history(f):
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
    b = ctx["facts"]["branch"]
    if b and b != "main":
        yield Finding("branch-name", "info", None, None,
                      f"default branch is {b!r}; every other repo uses 'main'")


RATIONALE = {
    "missing-required": "Community-standard files absent; 5 repos lack CONTRIBUTING today.",
    "license-posture": "ADR 0007: proprietary org-wide; OSS headers predate the decision.",
    "canon-drift": "Mechanical files have one correct form; drift is a bug, not a variant.",
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
    "licence-copyleft": "AGPL dependencies under a proprietary posture need a human call.",
    "phantom-command": "A documented command with no target is a lie, not a gap.",
    "unverified-command": "8 of gestion's 14 documented make commands are run by no gate.",
    "readme-sections": "Presence, never order; archetype decides the extras.",
    "orphan-reference": "custom apps/ holds 7 dirs with no repo in the org.",
    "absolute-path": "AGENTS.md:32 hardcodes /srv/syncthing/CESFAMS.",
    "personal-data": "Names and personal addresses belong in CONTRIBUTORS/LICENSE only.",
    "doc-language": "Repo docs English; only the org profile is bilingual.",
    "nested-repo": "epidemiologia sits inside gestion/apps with no .gitmodules.",
    "branch-name": "analizador-rem is on master; the rest are on main.",
}


# ---------------------------------------------------------------- settings

@setting("dependabot-alerts")
def _s_dependabot(action, ctx):
    repo = ctx["facts"]["repo"]
    if action == "probe":
        code, _, _ = sh(["gh", "api", f"repos/{ORG}/{repo}/vulnerability-alerts"])
        return code == 0
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
    """Non-negotiable pre-flight. Enforcing 2FA removes members who lack it —
    and the only member is the owner."""
    out = gh("api", f"orgs/{ORG}/members?filter=2fa_disabled", "--jq", ".[].login")
    return [m for m in str(out or "").split("\n") if m]


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
            print(f"SKIP    {name:<20} needs org-scoped auth (--offline)")
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
        added, gone = sorted(now - was), sorted(was - now)
        total_new += len(added)
        total_gone += len(gone)
        if not old:
            print(f"  {repo:<16} {len(now)} findings recorded (first baseline)")
            continue
        print(f"  {repo:<16} +{len(added)} new  -{len(gone)} resolved  ={len(now & was)} open")
        for fp in added[:6]:
            print(f"      NEW      {fp}")
            new_by_rule.setdefault(fp.split('|')[0], set()).add(repo)
        for fp in gone[:6]:
            print(f"      RESOLVED {fp}")
    # A rule appearing across most repos at once is a rule change; documentation does not
    # rot in lockstep. Requiring ALL of them was too strict — one already-compliant repo
    # (repo-docs itself) was enough to silence the warning.
    for rulename, repos in sorted(new_by_rule.items()):
        if len(repos) >= 2 and len(repos) >= len(current) / 2:
            print(f"\n  ! {rulename!r} is new in {len(repos)} of {len(current)} repos "
                  f"— suspect the rule or a canon change, not the documentation")
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
                         "--head", branch, "--base", facts["branch"] or "main",
                         "--title", f"docs: {level} pass",
                         "--body", "Documentation pass from `repo-docs`. Draft: prose needs a "
                                   "human read before merge.\n\nRun `docs.py check <repo> "
                                   "--explain` to see what remains."])
    return out if code == 0 else f"branch pushed, PR not created: {err[:200]}"


def selftest() -> None:
    global ROOT
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
            "A three-person team works here.\n")
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
            assert any(f.rule == "adr-status" for f in _r_adr(ctx))
            assert any(f.rule == "fact-contradiction" for f in _r_contradiction(ctx)), \
                "three-person vs single developer must contradict"
            assert "SECURITY.md" in gaps(facts, "full", False)

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
