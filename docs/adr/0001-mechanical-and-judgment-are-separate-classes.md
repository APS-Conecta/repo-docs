# Documentation splits into a mechanical class and a judgment class

- Status: Accepted
- Date: 2026-08-07

## Context

The tool had to decide what it generates and what it merely checks. The obvious framings were both
wrong. Templating everything makes every README the same document with the nouns swapped.
Templating nothing lets issue-form YAML drift apart across seven repositories, and then the checker
spends its life reporting differences nobody intended.

The organisation already had a house style in `gestion` — issue forms, a PR template, `CODEOWNERS`,
a proprietary licence, a pre-commit guard. Imposing generic scaffolding over it would have replaced
something that works with something generic.

## Decision

Every documentation artifact belongs to exactly one class.

**Mechanical** artifacts have one correct form across the organisation. They are held in `canon/`,
generated from it, and repaired to it by `--fix`. Difference is drift, and drift is a defect.

**Judgment** artifacts have no single correct form. A human or model authors them. The tool checks
their *structure* — required sections present, links resolve, commands exist — and never rewrites
their prose.

`canon/` is refreshed from `gestion` by `harvest`, so the house style has one home and the tool is
downstream of the project that earned it rather than parallel to it.

A third state was forced by an incident during construction: **Seed**. `LICENSE` and `CHANGELOG.md`
look Mechanical at creation and are not. They accumulate repository-specific content, so they are
written once when absent and never restored. Treating a Seed as Canon destroys content — `--fix`
was one run away from erasing a changelog by "restoring" it from its skeleton.

## Considered Options

**Template everything, `--fix` everything.** Maximum automation and the strongest consistency
guarantee. Rejected: the output reads as templated, and prose that a machine rewrites is prose
nobody owns.

**Template nothing.** Maximum flexibility, smallest tool. Rejected: the mechanical files then drift
by default and the checker can only complain about differences it could have prevented.

**Seed everything (never repair).** Safe, and gives up the one thing machines are reliably better
at than people: making seven copies of a YAML file identical.

## Consequences

- `--fix` is safe to run unattended on the Mechanical class and is never offered for prose.
- The classification is the first question asked of any new artifact. Getting it wrong is
  destructive in one direction (Seed treated as Canon) and merely annoying in the other.
- `canon/` must be re-harvested when `gestion` evolves; hand-editing it forks the house style.
- The tool cannot improve the quality of writing. It can only guarantee that the writing is
  structurally complete and factually consistent — which is the part that can be checked.
