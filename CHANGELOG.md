# Changelog — repo-docs

Tuning log. One line per rule change, naming the repo that taught it. The skill stays short because
its history lives here.

Format: [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added — second pass: authoring, growth, licences

- **Profiles.** Policy left the engine. `profiles/_base.json` holds craft, `profiles/aps-conecta.json`
  holds decisions; a profile parameterises rules, never defines them (ADR 0002). Selected by remote
  owner. An owner with no profile is **unmanaged** and refused — 49 third-party clones share the
  same disk, and absence of policy must not become a default.
- **Section Contracts.** `scaffold` writes a README outline with the sections that archetype owes
  and what each must contain, instead of a bare `$PLACEHOLDER`. The same contract gates
  `readme-sections`, so what is asked for and what is accepted cannot drift. `unfilled-contract`
  (error) fails any marker that ships — a shipped outline looks like documentation and is not.
  New: `docs.py outline <repo>`.
- **Baseline.** `baseline.json` records findings per repo; `--all` diffs against it and
  `--save-baseline` records. Distinguishes a documentation regression from a **rule** regression —
  a rule new in every repo at once broke, and the run says so. First baseline: 119 findings
  across 4 repos.
- **`phantom-command`** (error) and **`unverified-command`** (warn). A documented command with no
  target is false; one no gate runs violates "never assert what you haven't run". Found 9
  unverified `make` commands in `gestion` against `cleanboot` and `ci`.
- **Licence coverage** — `licence-declaration` (error), `licence-inventory` (warn),
  `licence-copyleft` (warn), plus `docs.py licences <repo>`. A repo declares its licence in up to
  four places read by four different tools; third-party licences are inventoried from
  `composer.lock`, `node_modules`, vendored app dirs and compose images, then reconciled against
  the notices document.

### Removed

- **`DENYLIST`.** Measured across all four repos: it excluded **zero** files. `git ls-files` plus
  the nested-repo halt already draw the boundary, because vendored apps are committed as tarballs.
  Deleted per the skill's own doctrine rather than maintained. Prediction that it would rot as
  apps accumulate was wrong — it never fired at all.

### Fixed — second tuning pass

- `phantom-command` parsed English prose as commands: "make it", "make the", "make this",
  "make two", "make one", "make some", "make target" — seven false positives from the verb.
  Detection now requires code voice: inside backticks or a fenced block.
- `RETIRED` included `was`, which appears in ordinary prose and silently suppressed a real
  phantom in `BUGS.md`. Tightened, and dated history (ADRs, CHANGELOG, BUGS, ROADMAP) is exempt
  per `CONTRIBUTING.md`'s own carve-out.
- Retirement acknowledgement was matched on the finding's own line, but Markdown prose wraps —
  `make credentials` in `CONTRIBUTING.md:49` is acknowledged as deleted on line 50. The window is
  now the surrounding paragraph.
- `discover` dumped 49 unmanaged third-party clones as a wall of names; collapsed to counts by
  owner.

### Findings this pass surfaced

- `territorio` declares AGPL-3.0 in `appinfo/info.xml`, `composer.json` and `package.json` while
  shipping **no LICENSE file**, under a proprietary posture.
- `territorio` bundles `@nextcloud/vue` (AGPL) and four GPL packages into built JavaScript. That is
  linking, not arm's length, and it needs a human decision rather than a rule.
- `gestion` vendors `apps/eurooffice` (AGPL) and runs four container images with no
  machine-readable licence.

### Added

- Initial skill: `discover` · `scan` · `check` · `audit` · `harvest` · `scaffold` · `settings` ·
  `pr` · `selftest`, with registries `DENYLIST` `STACK_MARKERS` `ARCHETYPES` `CANON` `LEVELS`
  `CHECKS` `FACTS` `SETTINGS` `CLAIM_BOXES`.
- 16 rules and 5 facts, seeded from defects found in `gestion`, `epidemiologia`, `territorio`
  and `analizador-rem`.
- `canon/` harvested from `gestion` — issue forms, PR template, CODEOWNERS, proprietary LICENSE,
  pre-commit hook.
- `public/` — org-safe CONTRIBUTING and SECURITY for the world-readable `.github` repo.

### Fixed — first tuning pass, all taught by `gestion` unless noted

- `licence` fact read every mention of MIT/Apache anywhere, so `docs/LICENSING.md` — the
  deliberate third-party audit ADR 0007 requires — reported 8 false violations. Claims now come
  only from `README.md` and `LICENSE*`, and only from lines that self-refer. `epidemiologia`
  then showed why: its README says "Apache-dependent", meaning the **web server**.
- `stack_versions` compared whole dicts, so "Nextcloud 34", "PostgreSQL 18" and "Redis 8" looked
  like three contradictory values of one fact. Claims now carry a **subject**; only same-subject
  claims can contradict.
- `absolute-path` excluded backticked paths, which silently hid the one real instance
  (`AGENTS.md:32`, `/srv/syncthing/CESFAMS`). Backticks no longer exempt. Conversely it fired on
  `/var/www/html/…` — a container path, legitimately absolute — so only host-side prefixes
  (`/srv`, `/home`, `/Users`, `/mnt`) count now.
- `readme-sections` read `##` headings only, so it missed a status stated in a blockquote bold
  lead-in and a licence stated in a file-map table cell. Headings, bold lead-ins and table rows
  all count as a section.
- `claim-boxes` fired on `PULL_REQUEST_TEMPLATE.md`, whose boxes *are the form*. Templates skipped.
- `personal-data` flagged `git@github.com` (an SSH host, not an address) and the copyright holder
  named in `docs/LICENSING.md`, where naming them is the point. Both allowlisted.
- `adr-status` demanded the literal phrase "superseded by" immediately before a link; ADR 0000
  writes "Superseded on the `themes/` half** by [ADR-0001](…)". A forward link anywhere on the
  line now counts.
- `canon-drift` wanted to restore `LICENSE` and `CHANGELOG.md` from `canon/`. `--fix` would have
  **destroyed changelog history**. Both are now `CANON_SEED_ONLY`: written once when absent, never
  restored. Caught before it ran on a real repo.
- `orphan-reference` flagged `Epidemiología` as a repo that does not exist — it is the accented
  local directory name for the repo `epidemiologia`. Comparisons normalise accents and spacing.
  Taught by `epidemiologia`.
- `license_kind` had no AGPL branch, so `analizador-rem` and `epidemiologia` reported the vague
  `other` instead of the real finding: both ship **AGPL-3.0**, which ADR 0007 requires reconciling.
  Taught by `analizador-rem`.
- `settings` reported private-vulnerability-reporting and secret-scanning as **FAILED** on
  `gestion`. Both are public-repo features and cannot be enabled on a private repo without
  Advanced Security. They now carry `scope="public"` and report `n/a`, and `claim-boxes` stops
  treating their checklist items as machine-verifiable there.

- `public-leak` flagged `PULL_REQUEST_TEMPLATE.md`'s checkboxes as unchecked hardening items.
  Same class of error as `claim-boxes`: a template's boxes are the form. The unchecked-box pattern
  now skips templates; the other leak patterns still apply to them.
- `open_pr` was specified in the plan and never implemented — the `pr` subcommand did not exist.
  Added, with the dirty-tree refusal it was supposed to have.
- `sh()` strips stdout, which eats the leading space of `git status --porcelain`'s status column,
  so ` M README.md` arrived as `M README.md` and a fixed `[3:]` slice truncated the filename to
  `EADME.md`. Porcelain lines are now split, never sliced, and `selftest` exercises a
  **modified tracked** file rather than only an untracked one — the untracked case masked the bug.
- `pr` treated every dirty file as intended, which voided the "refuses on a dirty tree" guarantee
  it advertised. It now commits only documentation paths and refuses outright when anything else
  is dirty.

Net effect on `gestion`: 23 errors → 7, every survivor a true positive.

### Changed

- `docs.py` is vendored into each repo as `.github/repo-docs.py` and kept in sync by `canon-drift`,
  so CI runs it without cloning anything. Its personal defaults (root, org, holder) moved to
  `config.json` / env vars, because one of the repos it ships to is public.

### Applied to GitHub

- `2026-08-07` — Dependabot alerts **enabled** on `APS-Conecta/gestion` during plan verification
  step 7. `org-2fa` refused at its pre-flight: `ddespinoza` is the only member and has 2FA
  disabled, so enforcing it would have locked the org's owner out.
