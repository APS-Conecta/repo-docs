# Context — repo-docs

Glossary for the documentation-control domain. Terms only; no implementation, no decisions.
Decisions live in `docs/adr/`.

## Governed Surface

The set of files this skill is responsible for in a given repo: git-tracked Markdown, minus the
denylist, minus anything inside a nested repository. Not "all Markdown" — vendored upstream
documentation is present in the tree but is someone else's work and outside the surface.

A file outside the Governed Surface is never audited, never fixed, never counted.

## Mechanical / Judgment

The two classes every documentation artifact falls into.

**Mechanical** — has exactly one correct form across the organisation. Issue forms, PR template,
CODEOWNERS, the pre-commit hook, the CI workflow. Any difference between two repos is drift, i.e.
a defect. Machines generate these and machines repair them.

**Judgment** — has no single correct form. README, CONTRIBUTING body, SECURITY wording, ADRs,
how-to guides. A human or model authors these; the skill may check their *structure* but never
rewrites their prose.

The classification decides who writes a file and whether `--fix` may touch it. It is the primary
distinction in this domain.

## Canon / Seed

**Canon** — the authoritative copy of a Mechanical artifact, held once in the skill and propagated.
Drift from Canon is a finding and is repairable.

**Seed** — an artifact written once when absent and never afterwards restored, because it
accumulates repo-specific content. `LICENSE` and `CHANGELOG.md` are Seeds. Treating a Seed as Canon
destroys content: restoring `CHANGELOG.md` from its skeleton erases the changelog.

Seed and Canon look identical at creation and differ entirely thereafter.

## Claim / Authority / Fact

**Fact** — a proposition about the repo or organisation that documentation asserts and that can be
independently established. Team size, licence, default branch, stack versions, repo visibility.

**Authority** — the single source that settles a Fact. The GitHub API for membership, the `LICENSE`
file for licence, `compose.yaml` for stack versions. One Fact, one Authority.

**Claim** — one documentation line asserting a Fact. A Claim carries a **subject** when the Fact is
compound: "Nextcloud 34" and "Redis 8" are Claims about different subjects of one Fact and cannot
contradict each other.

A Claim is only *ours* when its line self-refers. "Apache-dependent" in a README names a web
server, not a licence position.

Two failures are distinct: **contradiction** (two Claims disagree) and **drift** (a Claim disagrees
with its Authority). A repo can be perfectly self-consistent and uniformly wrong.

## Archetype

What kind of thing a repo is — app, nextcloud-app, website, library, org-profile — inferred from
stack markers rather than declared. The Archetype decides which sections its README owes.

## Section Contract

The sections an Archetype owes, each paired with an authoring prompt and a checkable condition.
One definition serves three roles: it generates the outline, it tells the author what the section
must contain, and it gates the result. Because generation and gating read the same definition, what
the skill asks for and what it accepts cannot drift apart.

A **section** is satisfied by a heading, a bold lead-in, or a file-map table row — presence is what
matters, never order. A repo may state its status in a blockquote and its licence in a table.

## Open Commitment

An unchecked checklist item in documentation: work the docs promise and reality has not delivered.
Distinct from a **form field**, which is an unchecked box in a template awaiting a future author —
identical in syntax, opposite in meaning.

An Open Commitment whose Fact has an Authority is **verifiable** and may be corrected automatically.
One whose promise is unachievable on that repo — a public-repo feature promised on a private repo —
is not open work but a wrong commitment, and must be rewritten rather than ticked.

## Finding

One defect, located. Severity is a claim about consequence, not confidence: **error** blocks,
**warn** informs, **info** records something true that the skill will not act on. A rule that
cannot state a consequence should not have a severity.

## Craft / Decision

The axis that separates the engine from a Profile.

**Craft** is what makes documentation correct anywhere: a link resolves or it does not, an ADR
without a status cannot be superseded, a documented command that does not exist is a lie, a Claim
must match its Authority. Craft has no opinions about licences or languages.

**Decision** is what one organisation chose: that its code is proprietary, that its docs are in
English, that a Nextcloud app is a recognised Archetype. Every rule in the engine is Craft; every
rule's parameters are Decision.

Mixing the two is what makes a tool unportable. The Profile is the seam that keeps the engine
agnostic — not overhead on top of it.

## Profile

The Decision layer for one owner, as data rather than code. A Profile parameterises rules and
facts; it never defines them, so it can be read at a glance instead of reviewed as code.

Profiles compose: a base holds universal convention, an owner's profile overrides and extends.
A Profile is selected by the repository's remote owner.

## Unmanaged

An owner with no Profile. Third-party clones sitting on the same disk are Unmanaged: the skill
refuses to operate on them rather than falling back to a default. Absence of policy is a refusal,
never an assumption.

## Baseline

The last recorded set of Findings, per repo. A run is read against it: which Findings are new,
resolved, or persistent.

The Baseline is what makes improvement observable and what distinguishes a **documentation
regression** (one repo gains findings) from a **rule regression** (every repo gains the same
finding at once — the rule broke, not the docs).

## Documented Command / Verified Command

A **Documented Command** is any command the Governed Surface tells a reader to run.

It is **Verified** when some automated gate runs it. Unverified, it is an assertion nobody has
tested — which the documentation rules forbid — and must either be covered by a gate or marked
untested where it appears.

A Documented Command with no corresponding target, script or recipe is a **Phantom**: the
documentation is not merely unverified but false.

## Nested Repository

A git repository inside another repository's working tree with no submodule registration. It
belongs to neither surface cleanly: its files are not the parent's to document, and walking into it
misattributes them. The boundary is respected, never repaired — restructuring a working tree is
outside this domain.
