# Craft lives in the engine, decisions live in a profile

- Status: Accepted
- Date: 2026-08-07

## Context

The tool was built for one organisation and hardcoded its choices: proprietary licensing from
ADR 0007, English-only documentation, Nextcloud and WordPress archetypes, one organisation's
security-checklist wording, one copyright holder, one root directory on one machine.

Reviewing the seventeen rules against that made the seam obvious. **Not one rule is
organisation-specific in its logic.** `license-posture` does not know what a licence should be; it
knows a repository declares one and that it must match its authority. `doc-language` does not
prefer English; it detects a language and compares it to a target. Every rule is a general law, and
every rule is parameterised by a local choice.

Leaving those parameters inline meant the engine could never be pointed anywhere else, and meant
tuning policy required editing a thousand-line file.

## Decision

Two layers.

The **engine** encodes craft: what makes documentation correct anywhere. A link resolves or it does
not. An ADR without a status cannot be superseded. A documented command that does not exist is a
lie. A claim must match its authority. The engine has no opinions about licences or languages.

A **profile** encodes decisions: what one owner chose. Profiles are data, not code — they
parameterise rules and facts but never define them, so a profile is read at a glance rather than
reviewed as a program. `_base.json` carries universal convention (Diátaxis, Keep a Changelog, MADR,
generic archetypes); an owner's profile overrides and extends it.

A profile is selected by the repository's remote owner. An owner with no profile is **unmanaged**
and the tool refuses to operate on it. Third-party clones share the same disk, and absence of
policy must be a refusal rather than a default.

Only the `APS-Conecta` profile ships. The layer exists to keep the engine honest, not because a
second tenant is planned.

## Considered Options

**Policy in `config.json`.** Ten lines, no new files, and enough for licence, language and holder.
Rejected as too shallow: archetypes, section contracts and claim boxes are policy too, and they do
not fit in a flat key-value file. It would have deferred the same work at a worse moment.

**Executable profiles.** A profile could define its own rules inline, with full expressiveness.
Rejected: adding an organisation would mean writing code, and every profile would need reviewing as
code rather than read as policy.

**Stay single-tenant.** Honest about there being one tenant. Rejected because the separation earns
its place even at one — it is what stops organisation-specific assumptions leaking back into rules,
which is precisely how the licence rule got its first three false positives.

## Consequences

- Adding an organisation is a JSON file. Adding a *rule* is still Python, deliberately.
- The engine can be tested against a synthetic profile, which the selftest now does implicitly.
- Two files must be read to know why a rule fired. `--explain` exists to close that gap.
- A profile can silently disable a rule. Rule coverage therefore has to be visible in output —
  a skipped rule prints as skipped, never as a pass.
- `repo-docs` becomes the eighth repository in the organisation and is held to its own rules, so a
  rule that is painful to satisfy is felt by its author first.
