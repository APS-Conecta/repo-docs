# A documentation tool changes GitHub settings

- Status: Accepted
- Date: 2026-08-07

## Context

`SECURITY.md` in `gestion` carries a hardening checklist with unchecked boxes. Probing the API
showed three of them were genuinely open — organisation 2FA not enforced, Dependabot alerts off,
private vulnerability reporting off — and that the documentation was, at that moment, honest.

Nothing kept it honest. A checklist is a backlog hiding in a document: it drifts from reality in
both directions, and neither direction is visible. Boxes stay unticked long after the work is done,
and stay ticked after a setting is turned off.

The tool could already read the truth. The question was how far it should go once it knew.

## Decision

The tool verifies documented claims against the GitHub API, corrects the **documentation**
automatically, and — under an explicit `--apply-settings` — also changes the **settings** so that
documentation and reality converge rather than merely being reported as divergent.

One setting is fenced. Enforcing organisation-wide 2FA removes members who have not enrolled.
`APS-Conecta` has exactly one member, `ddespinoza`, who is also the owner and does not have 2FA
enabled. Applying it would have locked the owner out of the organisation.

So `org-2fa` carries a pre-flight: the tool lists every non-compliant member, refuses while that
list is non-empty, and prints the forced order — enrol the accounts, then enforce. Every other
setting is reversible and applies directly.

Settings that GitHub only offers on public repositories — private vulnerability reporting, secret
scanning without Advanced Security — are reported as not applicable rather than as failures. A
checklist item promising them on a private repository is not open work; it is a wrong commitment
and must be rewritten.

## Considered Options

**Report only.** The conservative choice, and the one originally recommended: tell the human, let
them click. Rejected by the author on the grounds that a report nobody acts on is how the checklist
got stale in the first place.

**Apply everything including 2FA.** Fastest convergence. Rejected: an irreversible action taken as
a side effect of a documentation run is not a trade-off, it is an accident waiting for a quiet
afternoon.

**Never touch settings, only tick boxes.** Keeps the tool inside its stated domain. Rejected as the
worst of both — it makes documentation agree with reality by editing the documentation, which is
the direction that loses information.

## Consequences

- A documentation tool now holds `admin:org`. That is a real expansion of blast radius and the
  reason `--apply-settings` is opt-in per run rather than implied by `--fix`.
- The pre-flight is the only thing standing between a routine docs pass and an organisation
  lockout. It is asserted in the selftest and must never become advisory.
- CI cannot run this half: `GITHUB_TOKEN` is repository-scoped and cannot read organisation facts.
  The rule set is therefore split, and the gate runs the offline subset.
- Dependabot alerts were enabled on `gestion` on 2026-08-07 during verification. The first real
  change this tool made to the organisation was made by the tool, not by a human, which is exactly
  the property this record exists to make visible.
