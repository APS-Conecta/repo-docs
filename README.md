# repo-docs

Documentation control for the APS Conecta repositories. It audits what is already written, corrects
what has one provably right answer, and scaffolds what is missing.

## What this is — and what it is not

**It is** an auditor first. The organisation's documentation already exists and is already drifting:
four files in `gestion` disagreed about the size of the team, three repositories declared a licence
their `LICENSE` file contradicted, and twenty-two ADRs had no status field between them. This tool
finds that class of defect and, where a machine can settle the question, fixes it.

**It is not** a writing assistant. It cannot make prose good. It checks that documentation is
structurally complete and factually consistent — the part that can be checked — and leaves the
writing to a person or a model working from the section contract it generates.

**It is not** a generic tool. It encodes this organisation's decisions in `profiles/aps-conecta.json`.
The engine is portable; the policy is not, and that separation is deliberate ([ADR 0002](docs/adr/0002-craft-in-the-engine-decisions-in-a-profile.md)).

## Status

**Working, in first rollout.** 25 rules, 5 facts, 5 settings probes, one profile.

Verified against all six cloned repositories. It governs itself: this repository is the eighth in
the organisation and must pass its own gate.

Not yet done: the org-wide `.github` defaults pass, two repositories are not cloned locally
(`Databases` among them), and the licence reconciliation ADR 0007 requires is still open on
`territorio` and one other repository.

## Quickstart

Everything below runs on the host, from any directory.

1. Point the tool at your clones. Runs once per machine.

   ```bash
   cp config.example.json config.json
   $EDITOR config.json          # set "root" to the directory holding your clones
   ```

   `config.json` is gitignored — it holds a machine path, never policy.

2. Confirm it can see the repositories.

   ```bash
   python3 scripts/docs.py discover
   ```

   Expect a JSON map of every clone whose owner has a profile. Owners without one are listed under
   `unmanaged` and are never touched. An empty `repos` map means `root` is wrong.

3. Audit one repository.

   ```bash
   python3 scripts/docs.py check gestion --explain
   ```

   Exit code 0 means no errors; 1 means at least one. Warnings never fail. `--explain` prints why
   each rule exists, so a finding you disagree with names the line to edit.

4. Audit everything and record the result.

   ```bash
   python3 scripts/docs.py check --all --save-baseline
   ```

   Later runs diff against `baseline.json`: what is new, what is resolved, what is still open.

If a step fails, the message names the cause. The most common is `root` pointing somewhere with no
clones in it.

## Install

No dependencies. Python 3.9 or newer, `git`, and `gh` authenticated with `repo` and `admin:org` for
the rules that read organisation state.

The skill is loaded by symlink, so the repository and the skill are the same files:

```bash
ln -s "$PWD" ~/.claude/skills/repo-docs
```

Verify with `python3 scripts/docs.py selftest`, which builds a temporary repository and asserts the
destructive paths are safe.

## Commands

| Command | Does |
|---|---|
| `discover [--clone]` | Map managed clones; refuse unmanaged owners |
| `scan <repo>` | Inventory as JSON. Never writes |
| `check <repo\|--all>` | The gate. `--fix`, `--offline`, `--explain`, `--save-baseline` |
| `outline <repo>` | The README section contract and what is missing from it |
| `licences <repo>` | What the repo declares, and every third-party licence present |
| `scaffold <repo> --write` | Write missing files. Never overwrites |
| `harvest` | Refresh `canon/` from the profile's exemplar |
| `settings <repo>` | Probe GitHub state; `--apply-settings` to change it |
| `pr <repo>` | Draft PR of documentation changes only |
| `audit <repo>` | Prompt for a full model read. Not part of the gate |

Rules, facts and settings are registries: adding one is a function and a decorator. Policy is a
table in a profile. If tuning requires editing a function body, the seam is wrong.

## Consumers

Nothing imports this. It is invoked as a CLI, and vendored into each governed repository as
`.github/repo-docs.py`, where the `docs` workflow runs its offline rules on every pull request.
`canon-drift` keeps those copies identical to this one, so this repository is the only place the
engine is edited.

Changing a rule therefore changes every repository's gate at the next `--fix`. Read
[`CONTEXT.md`](CONTEXT.md) before adding one — the vocabulary is load-bearing.

## Licence

GNU Affero General Public License v3.0 or later — see [`LICENSE`](LICENSE). This matches the
organisation-wide posture recorded in
[gestion ADR-0010](https://github.com/APS-Conecta/gestion/blob/main/docs/adr/0010-agpl-across-the-org.md),
which moved to `gestion` from a product repository on 2026-08-08 because an org-wide decision does
not live in one product's repository. The
tool depends on nothing outside the Python standard library, so there are no third-party notices to
carry.
