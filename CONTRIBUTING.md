# Contributing — repo-docs

This tool governs the organisation's documentation, so a change here changes every repository's
gate. The organisation-wide contract in `APS-Conecta/.github` applies; what follows is what differs.

## The one rule that matters

**A rule that fires wrongly is a defect in this repository, not in the document it flagged.**

Hand-editing the document to silence a finding loses the lesson and leaves the rule broken for every
other repository. Fix the rule or the table it reads, re-run `check --all`, and log one line in
[`CHANGELOG.md`](CHANGELOG.md) naming the repository that taught it.

Every entry in that changelog is a false positive this tool produced against real documentation.
That list is the most useful thing here — keep adding to it.

## Craft or decision

Before adding anything, decide which layer it belongs to ([ADR 0002](docs/adr/0002-craft-in-the-engine-decisions-in-a-profile.md)):

- **Craft** — true of documentation anywhere. A broken link is broken in any repository. Goes in
  `scripts/docs.py` as a rule.
- **Decision** — what this organisation chose. That our code is AGPL-3.0-or-later, that our docs are in
  English. Goes in `profiles/aps-conecta.json` as data.

A rule that hardcodes a decision is the mistake to avoid; it is how the licence rule earned its
first three false positives.

## Adding a rule

```python
@rule("my-rule", "warn", offline=True)
def _r_mine(ctx):
    """Why this exists. Shown by --explain."""
    yield Finding("my-rule", "warn", file, line, "what is wrong")
```

`offline=False` marks a rule needing organisation-scoped auth; it is excluded from the CI gate,
because CI's `GITHUB_TOKEN` cannot read organisation state. Add the rationale to `RATIONALE`.

Severity is a claim about consequence, not confidence. `error` blocks a merge. If you cannot say
what breaks, it is a `warn`.

## Before you push

```bash
python3 scripts/docs.py selftest      # asserts the destructive paths are safe
python3 scripts/docs.py check --all   # no new findings you did not intend
python3 scripts/docs.py check . --fix # this repo passes its own gate
```

`selftest` must stay fast and dependency-free. It exists because `--fix` writes to real
repositories: it was one release away from erasing a changelog, and the assertion that caught that
class is why `LICENSE` and `CHANGELOG.md` are seeds rather than canon
([ADR 0001](docs/adr/0001-mechanical-and-judgment-are-separate-classes.md)).

## Deleting rules

A rule that has never fired across the organisation gets deleted, not kept in case. `DENYLIST` was
measured at zero exclusions and removed. Coverage is not the goal; catching real defects is.

## Vocabulary

[`CONTEXT.md`](CONTEXT.md) is the glossary and is load-bearing — *canon* and *seed* look identical
at creation and differ entirely afterwards, and confusing them destroys content. Read it before
naming anything new.
