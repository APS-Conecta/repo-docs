# Conventions

## Diátaxis — one page, one mode

Two axes: theory↔practice, study↔work.

| mode | orientation | quadrant | answers |
|---|---|---|---|
| Tutorial | learning | study + practice | "teach me, I'm new" |
| How-to guide | task | work + practice | "I need to do X" |
| Reference | information | work + theory | "what are the parameters" |
| Explanation | understanding | study + theory | "why is it like this" |

Mixing modes on one page is the most common documentation failure. A tutorial that stops to
enumerate every flag has become reference and stopped teaching.

## Changelog

Keep a Changelog 1.1.0 + SemVer 2.0.0. `## [Unreleased]` always present. Groups in order:
Added · Changed · Deprecated · Removed · Fixed · Security. Entries describe the change for a human
reading it later, not the commit that made it.

`CHANGELOG.md` is a **seed**, not canon — written once when absent, never restored from the
skeleton. Restoring it would destroy history.

## ADRs — MADR

Sequential, per repo, from `0001`. Never renumber; numbers are addresses. Filename
`NNNN-kebab-summary.md`.

`Status:` is mandatory — `Proposed` · `Accepted` · `Superseded by NNNN`. A superseded ADR stays in
place and links forward on the line that says so; nothing may link to a superseded ADR silently.
The record of a decision is the point, so a deleted ADR is a deleted reason.

Numbering is per repo, so `0001` exists several times across the org. That is intended — an ADR
address is `repo/docs/adr/NNNN`, never `NNNN` alone.

## Commits and branches

Conventional Commits: `feat:` `fix:` `docs:` `chore:` `test:` `refactor:`. Branches off the default:
`feat/…` `fix/…` `docs/…` `chore/…`, short-lived. AI-assisted PRs carry the `ai-assisted` label and
disclose it in the description.

## Badges

Build · version · licence. Three maximum. A badge pointing at a dead service is worse than no
badge — it asserts a status nobody is checking.

## Language

Repo documentation in English: README, CONTRIBUTING, SECURITY, ADRs, everything under `docs/`.
The org `profile/README.md` is bilingual ES/EN — it is the public face of a Chilean organisation.

Spanish clinical and domain terms keep their Spanish name with a gloss on first use: CESFAM
(primary-healthcare centre), REM (statistical monthly return), APS (primary healthcare), Metas
Sanitarias (statutory health targets). Translating them loses the referent; they name real
institutions and instruments.

`analizador-rem` is the current outlier — `docs/ARQUITECTURA.md`, `DESARROLLO.md`, `ESTADO.md`,
`GLOSARIO.md` are Spanish. `GLOSARIO.md` arguably should stay: a glossary of Spanish domain terms
is reference material about Spanish, not documentation written in it.

## Licence posture

**AGPL-3.0-or-later org-wide** ([ADR 0010](https://github.com/APS-Conecta/gestion/blob/main/docs/adr/0010-agpl-across-the-org.md),
superseding ADR 0007). Inherited rather than chosen: the Nextcloud apps compile `@nextcloud/vue`
(AGPL-3.0-or-later) into the bundles they ship. "We use only open source" describes what the project
*consumes*; since ADR 0010 it describes what the project *produces* too.

The identity is protected by **trademark, not copyright**: logo, mono logo, lockup and favicon are all
rights reserved with the marks reserved under AGPL §7(e). Colour tokens ship under the AGPL — colour
values are functional data and copyright barely reaches them.

Third-party notices license other people's work and stay — `gestion/docs/LICENSING.md` is the full
audit. A licence name appearing in a doc is only *our* claim when the line self-refers ("our",
"this project", a `Licence:` label). "Apache-dependent" in `epidemiologia` means the web server.

Closed: the five repositories ADR 0007 left unreconciled — `analizador-rem`, `epidemiologia`,
`territorio`, `common`, `aps-conecta-web` — all now declare AGPL-3.0-or-later, verified against
GitHub on 2026-08-08.

## Reference documentation

Pull current library and framework docs from **Context7 MCP** — `resolve-library-id`, then
`query-docs` with the full question. Never hardcode API surfaces from memory; they rot silently and
a wrong flag in a doc costs more than a missing one. Context7 unavailable → `WebFetch` the canonical
upstream URL and cite the version. Never a hard dependency.

## Security-doc scope

A public `SECURITY.md` states scope, the private reporting channel, and what is deliberately out of
scope. It does not state what is not yet defended. Hardening checklists are operational backlog and
belong in the private repo — published, they are a list of open doors.

Private vulnerability reporting and secret scanning are **public-repo features**; on a private repo
without Advanced Security they cannot be enabled, so a checklist item promising them there is
unachievable and should be rewritten, not left unticked.
