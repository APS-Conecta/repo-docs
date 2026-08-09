# The checker is vendored into every repository

- Status: Accepted
- Date: 2026-08-09

## Context

CI must run the documentation gate in each repository. It cannot fetch this one.

A workflow's `GITHUB_TOKEN` is scoped to the repository it runs in. Every repository in the
organisation is private, so a job in `gestion` cannot clone `APS-Conecta/repo-docs` to get the
checker. The alternatives are a PAT held as an organisation secret, or making the checker public.

So each repository carries a copy: `.github/repo-docs.py` (1836 lines) plus `.github/profiles/`.
`canon-drift` compares the copy against `canon/` and reports a mismatch as an error, which is what
keeps eight copies from becoming eight versions.

Until 2026-08-09 this was recorded only as a three-line comment in `canon/workflows/docs.yml` and a
filename in `references/layout.md`. Neither states the constraint, so neither survives someone
deciding the duplication looks wasteful.

## Decision

Vendor the checker and its profiles into every repository, generated from `canon/`, and record the
constraint here rather than in a comment inside a generated file.

## Consequences

- **The cost is real and recurring.** 1836 lines × 8 repositories, refreshed by a chore commit
  whenever the engine changes. `canon-drift` makes a stale copy an error rather than a surprise.
- **It fails silently, and did.** The vendored copy had *never executed once* in any repository:
  `SKILL` was `Path(__file__).parent.parent`, correct for `repo-docs/scripts/docs.py` and wrong for
  `<repo>/.github/repo-docs.py`, so `profiles/` resolved one directory too high, `P` was `{}`, and
  every invocation died in argparse with `KeyError: 'levels'`. Eight repositories advertised a
  working `docs` workflow throughout; a real run on `aps-conecta-web` PR #1 carried the traceback.
  Fixed 2026-08-08 — resources now resolve from either location.
- **A vendored copy runs with less than the original.** `canon/` is not vendored, so `canon-drift`
  cannot evaluate itself in the repositories it governs; it reports SKIP there. That is deliberate
  and load-bearing: it must not pass silently for want of anything to compare against. The corollary
  is that a vendored *profile* drifts unnoticed between engine refreshes.
- **What replaces this.** An organisation PAT with read access to `repo-docs`, or publishing the
  checker as its own public repository. Either removes the duplication; the first adds a secret to
  rotate, the second publishes the audit rules. Neither was needed at eight repositories and one
  maintainer.
