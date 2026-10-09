# Changelog — repo-docs

Tuning log. One entry per rule change, naming the repo that taught it: the symptom, the root cause,
and how it was caught. The skill stays short because its history lives here — and the "how it was
caught" is the part that stops a defect recurring, so entries are as long as that takes.

Format: [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Removed

- **The `Docs:` trailer rule (scribe S1).** `pr-gate` no longer asks a PR touching `l10n/ src/ templates/
  appinfo/ lib/Command/ lib/Settings/` for `Docs: APS-Conecta/documentation#<n>` or `Docs: sin cambios`.
  The line was self-declared and nothing verified it; the scribe initiative's Scribe routine now reads
  every merged PR and writes the documentation itself. The profile keys `docs_line_paths` and
  `pr_exempt_logins` go with it (no reader left; the selftest now asserts their absence). The
  English-title check stays, for every login. Canon re-stamped; repo-docs' own copies re-rendered.

### Fixed

- **The R1b merge dropped five files; `main` went red (#8, #9, this entry).** Merging `main`
  into `feat/docs-es-r1b` (9345370) resolved its conflicts toward `main` and silently dropped
  R1b's `profiles/aps-conecta.json` keys, its re-rendered vendored copies, these CHANGELOG
  entries and its baseline re-record. Without `docs_line_paths` / `pr_exempt_logins`, `pr_gate()`
  watched nothing: the Docs-line rule passed every PR without checking it, and only the selftest
  caught it. #8 restores the keys (the same values R1b wrote) and re-renders the vendored copies.
  This entry restores the R1b CHANGELOG text below verbatim. The baseline is left to docs-es R2b,
  which re-records it when the census moves to the catalog.
- **`phantom-command` reads `composer run X` as the script `X` (#9).** The bare `composer`
  branch matched first, so "composer run test:unit" became the command `composer run` — a
  false ERROR on IntraVox `AGENTS.md:34`. `composer run` now precedes `composer` in
  `DOC_COMMAND`, and `available_commands()` offers both spellings of every composer script.

- **The census clone root.** The weekly sweep cloned the census into the repo-docs
  checkout (cwd-relative paths in `census.py run`), so `check --all` walked repo-docs
  holding the whole org nested inside it and went red on NEW findings a stale baseline
  could not absorb. `census.py run --root` now clones outside the checkout
  (`$RUNNER_TEMP/census` in CI, self-tested), the sweep points `REPO_DOCS_ROOT` there,
  and the baseline is re-recorded from clones at main so today's findings are open and
  only future drift is NEW — the drift itself is filed as one Task issue per repo.
  Two truths the re-record taught, both folded in here: `check --all` exits 1 on *any*
  open baselined error (41 sit open in AIO alone), so the sweep's verdict is now a grep
  for `NEW` lines over the full log — the red line its header always claimed — and the
  recorder must run with full auth (`--save-baseline` refuses degraded runs), which is
  a credential the sweep's own PAT lacks: it gets 403 on both dependabot setting
  probes, so gestion's two `could not read the setting` fingerprints are added to the
  baseline by hand, the way `common`'s were once removed by hand — the recordable run
  structurally cannot see what the weekly run will see every week until the PAT is
  widened (tracked as a Task in this repo).

### Added

- **actionlint guards the workflows.** The selftest job installs a pinned, checksum-verified
  actionlint 1.7.12 and lints `canon/workflows/*.yml` and `.github/workflows/*.yml` — the
  canon sources with their placeholders in place, so what parses is what renders. No pipeline
  check parsed workflow YAML before GitHub's runner did, and the R1b canon `docs.yml` shipped
  an unquoted `PR gate (Docs: line, English title)` step name — a colon-space in a plain
  scalar, a parse error only the runner caught, at startup, on the gate's own first live run.
  The selftest trigger widens to `.github/workflows/**` so every workflow change lints.

- **The PR gate: `pr-gate` and the unfiltered `docs` job.** Canon `workflows/docs.yml`
  loses its paths filter, gains `edited` among its pull_request types (editing the body
  to add the trailer re-runs the gate), runs as job id and name `docs` — the required
  check R5's ruleset will name — and installs a pinned, checksum-verified gitleaks
  8.30.1 over a full-depth checkout. Two checks run on pull_request only: a PR touching
  `l10n/`, `src/`, `templates/`, `appinfo/`, `lib/Command/` or `lib/Settings/` must carry
  a `Docs: APS-Conecta/documentation#<n>` or `Docs: sin cambios` line (the five
  automation logins are exempt from the trailer, never from the English-title rule),
  and every PR title must be English — the squash commit message is the title. The
  watched paths and exemptions live in the profile (`docs_line_paths`,
  `pr_exempt_logins`); the craft lives in the engine, where `pr-gate` reads the Actions
  event payload and derives its changed-file list from a merge-base diff over the same
  range scan uses.
- **`secrets` scans the PR commit range in CI.** The workflow exports
  `REPO_DOCS_PR_RANGE` (the PR's own commits; pushes scan just the pushed commits;
  empty only on a branch's first push) and `gitleaks_argv` turns it into
  `--log-opts` — a secret introduced by the PR fails the gate while history before the
  base never produces findings. Local runs and the weekly sweep, which never install
  gitleaks, keep the fallback regex path and a byte-identical invocation shape.
- **The Spanish opt-in: `docs_es` and the `.github/docs-es` marker (ADR-0006).** Opting in is
  one empty file, probed by `scan()` beside `has_ci` — a fact, consulted by the gated rules and
  nothing else. A repo that carries it loses the legacy aggregate `doc-language` warn (the
  per-file rule owns language from there) and its README answers the five-section Spanish
  contract; every repo that does not carries this whole round dormant — each gated rule reads the
  fact as its first line and returns, so non-opted repositories stay byte-identical through the
  change. repo-docs itself opts in: README, CONTRIBUTING and SECURITY are rewritten in the ADR's
  neutral register (third person or impersonal, infinitive steps, affirmative verified facts),
  `docs/index.md` is deleted (see Changed), and `docs/adr/0006-documentacion-en-espanol.md`
  records the decision.
- **Four rules for the Spanish surface: `doc-language-es` (error), the `readme-sections` Spanish
  contract (error findings under the unchanged `warn` registration — severity is per-Finding, and
  the exit count reads the Finding), `retired-paths` (error), `diataxis-verification` (warn,
  ungated).** `doc-language-es` holds the files `must_be_spanish` names org-wide — README,
  CONTRIBUTING, SECURITY, CODE_OF_CONDUCT — to Spanish body prose: fenced blocks and inline code
  blanked before tokenising, a 20-token floor at 5% density over the twelve closed stopwords, so
  a code-heavy Spanish page reads clean and a half-English one does not slip past;
  `must_be_spanish_documentation` adds `aviso.md` and four directory prefixes in the
  `documentation` repository alone, matched exact-or-prefix, never by suffix. The `readme-sections`
  contract holds opted-in READMEs to five ordered H2s — Qué es, Documentación, Estado, Inicio
  rápido de desarrollo, Licencia — with the Licencia section required to link the published
  aviso, checked offline against the link text; the `repo_readmes` fork keeps AIO's and
  IntraVox's `.github/README.md` under the same contract. `retired-paths` probes the working
  tree — an existence probe, not a tracked-Markdown walk — for the eighteen paths ADR-0006
  retired (`BUGS.md`, `docs/index.md`, the manuals subtree), so a committed stylesheet and an
  untracked leftover are equally defects. `diataxis-verification` requires a page whose front
  matter declares `tipo: guia` to carry a `Verificación` heading: three stdlib regexes over the
  leading block and the body, no yaml dependency, English repos included.
- **The mode table.** `docs/index.md` is rebuilt as the Document × Mode × Reader × Authority table —
  one row per governed document, `adr/0005-one-published-surface.md` included for the first time —
  and `references/layout.md` records the standard and the flat-`docs/` decision behind it: no
  Diátaxis directories at `full`, the table does the navigation. The `ultra` block keeps the
  four-directory definition and now records its own YAGNI — `required()` reads only the file list,
  so nothing enforces the split.
- **§Style in `references/conventions.md`** — sentence case, second person, active voice, present
  tense, blockquote admonitions — and the citation doctrine in §Reference documentation: Nextcloud
  facts pinned to `docs.nextcloud.com/server/34/`, cited never restated (occ reference,
  `config.php` parameters, `info.xml` schema, app-store rules, code signing, OCS/WebDAV APIs),
  fork deltas citing the upstream page, published pages never renamed.

### Changed

- **The baseline re-records the R1b canon movement: +16 new, −11 resolved, 12 keys.**
  Each canonized repository takes the workflow's canon-drift and a moved canon-stamp —
  the stamp message embeds both digests, so every canon byte that moves retires the old
  fingerprint — while their engine and profile drift fingerprints carry today's static
  messages and stay open until each R4 rollout re-renders its vendored set. The refresh
  also ran gitleaks-less for the first time (`PATH=/usr/bin:/bin`), so the three
  recorded `gitleaks flagged findings` fingerprints — written by a gitleaks-bearing
  machine, never reproducible on the sweep's runner — resolve permanently: the
  baseline now matches the ruleset the weekly sweep actually replays. gestion's two
  sweep-PAT claim-boxes fingerprints are carried by hand as before.
- **`docs/index.md` retires from `levels.full` and `levels.ultra`; `notices_doc` is
  `THIRD-PARTY-NOTICES.md` alone.** ADR-0006 puts navigation in the README's Documentación
  section — the flat index was a second navigation surface, and the four
  `missing-required` fingerprints it kept open (`absent: docs/index.md` in AIO, agents,
  pi-sandbox, rpiv-artifacts) become unproducible and resolve in the re-record below.
  `references/layout.md` now teaches the README-first tree and keeps the ultra block's Diátaxis
  definition with its YAGNI note. gestion keeps its `LICENSING.md` allowed by name but it is no
  longer the engine's notices document: the transitional `licence-inventory` warn the flip opens
  is accepted until the R4 rewrite (`_comment_notices_doc` records the decision, with the
  ADR-0006 pointer).
- **The baseline re-records the R1a suite: +33 new, −4 resolved, 12 keys, nothing stale.** The
  expected canon movement, not drift: the eight canonized repositories take four each — three
  `canon-drift` (the engine and both profiles differ from canon) and one `canon-stamp` (each
  vendored copy states the canon it was rendered from, and this round moved it) — gestion takes
  those four plus the accepted licence-inventory warn, and the four repositories that never
  vendored the checker keep their ten `missing; canon/… defines it` fingerprints byte-identical
  while losing exactly their `docs/index.md` absence. The re-render and the re-record ship in
  this same PR — an engine edit without a same-PR refresh turns the weekly sweep red between
  them — and the per-repo drift resolves itself as rollout PRs re-render each vendored copy.
  Recorded with full auth (`--save-baseline` refuses degraded runs); gestion's two sweep-PAT
  `claim-boxes` fingerprints — `could not read the setting`, the dependabot probes the sweep's
  token cannot make — are carried by hand, the way `common`'s were once removed by hand.
- **`doc_language_exempt` corrected to ten entries.** `GLOSARIO.md` is dropped — no such file
  exists anywhere in the suite — and the Spanish that actually ships is named instead:
  `docs/GUIA-CLINICA.md`, `docs/manual.md`, `Legal/OBLIGACIONES.md` and the six statute files, all
  matched by path suffix. The comment now states the reader/subject rule and records that
  gestion's `USER_MANUAL.md` is a deferral, not an exemption. This edit ages the canon stamp;
  every vendored copy is re-rendered to match.

### Fixed — seventh pass: the checker's own guards get wired and deduplicated

- **`harvest` refuses an exemplar it cannot name.** Without a remote its name pattern was two bare
  word boundaries — truthy, past the guard, matching between every word — and would have spliced
  the repo placeholder into every byte of every canon file. Asserted in `selftest`.
- **The render fixed-point assertion reads `canon_vars()`** instead of re-typing its seven names, so
  a variable added tomorrow is covered the day it exists.
- **`selftest` runs in CI** (`.github/workflows/selftest.yml`, this repository only — it needs
  `canon/` beside the checker). It was invoked by nothing.

### Fixed — sixth pass: the file stops leaking placeholders into itself

- **`harvest`'s substitution table was itself substituted, and every vendored copy carried the
  owner's real name where the table should hold a placeholder.** Found while fixing `SELF_REF`
  (#6) — same defect family, one layer further in. The table's replacement strings are the four
  names `render` supplies, so `canon/repo-docs.py` (a symlink to `scripts/docs.py`) rendered them
  out. It was visible in this repository's own vendored copy:

  ```python
  # .github/repo-docs.py, before
  subs = [(re.escape(HOLDER), "Daniel Espinoza Charrier"), (rf"\b{re.escape(name or '')}\b", "repo-docs"),
          (re.escape(ORG), "APS-Conecta"), (r"\b2026\b", "2026")]
  ```

  A table that replaces the owner's name **with the owner's name**. Inert only because `harvest`
  needs `canon/`, which is never vendored — had anyone run `harvest` from a vendored copy, it would
  have written real values into canon instead of placeholders.

  The dollar is now assembled at runtime (`D = "$"`), which `string.Template` leaves alone because a
  lone dollar matches none of its three forms. `$$` would not do: the source must *evaluate* to the
  placeholder, and `$$holder` evaluates to itself.

- **The fix is one assertion, not four.** `selftest` now asserts that **rendering this file changes
  nothing in it** — the invariant that makes the whole class impossible, rather than a check for the
  four tokens that happened to leak this time. `$SECTION_` and `$PLACEHOLDER` survive because they
  are not variables `render` supplies; anything that *is* one fails on the day it is written.

  It earned its keep immediately: the first run failed on the **comments explaining the trap**, which
  had been written with a live `$holder` in them. The explanation had fallen into the thing it
  explained, and only a byte-for-byte assertion could have noticed.

- **A vendored copy is now byte-identical to canon apart from its `CANON_STAMP` line.** That is the
  precondition for `canon-stamp` ever verifying a copy offline — not the verification: a copy still
  has no `canon/` to compare against and the rule still prints SKIP there, which is the open item
  ADR-0004 lists. (This bullet claimed the closure on 2026-09-13; corrected 2026-09-14.)

### Fixed — fifth pass: a placeholder that could not survive being rendered

- **A `$org` placeholder inside a regex could never match anything, in any copy.** `SELF_REF` — the
  sentence-scope test that decides whether a licence claim is *about us* — carried `APS Conecta|\$org`.
  `render` substitutes with `string.Template`, whose escape for a literal dollar is a doubled dollar
  and **not** a backslash, so the backslash survived into every vendored copy as `\APS-Conecta`: a
  leading `\A` is the start-of-string anchor, and the alternative matched nothing at all. The obvious
  repair is worse than the bug — a bare `APS-Conecta` also matches every `github.com/APS-Conecta/<repo>`
  URL in our own documentation, adding false positives to a rule whose severity is `error`. The name is
  now written out as `APS[- ]Conecta\b(?![-/])`, which folds in the spaced spelling, excludes the URL
  form, and — the point — holds no placeholder at all, so the line renders identically in canon and in
  every copy and cannot come back this way. Measured across all six clones at eight different gates:
  the candidate count is unchanged at every one of them, while the naive form raises it by between two
  and nine. Asserted both ways in `selftest`, which fails on the old pattern.
- **A repository deleted from GitHub rotted in the baseline, producing no output at all.**
  `baseline_diff` iterates `current`, so a recorded repository with no clone is neither new, resolved
  nor open — it simply never appears. `common` sat there after the repository was deleted and was
  found by hand-reading the JSON, not by running the tool. Names in the baseline and not in the run
  are now printed as `STALE <name> (recorded, no clone discovered)`. Verified by seeding a key for a
  repository that does not exist and watching it report.

### Added — fifth pass

- **`canon-stamp` (warn).** `canon-drift` needs both sides of a comparison and a vendored copy has
  only one: no repository carries `canon/` (ADR 0004), so the rule that keeps eight copies from
  becoming eight versions reports SKIP in the seven places those copies actually live. `render` now
  writes the digest of canon — `sha256[:12]` over every non-seed canon source — into the copy it
  produces, so a copy *states* which engine it came from instead of that being recoverable only by
  diffing it against a canon it cannot see. Where canon is present the rule compares the two and names
  version drift; where it is absent the stamp is printed and the run marked degraded, because an
  unevaluated rule must never read as green.
  The trap is that the stamp is written **into** a canon source — `canon/repo-docs.py` is a symlink to
  `scripts/docs.py` — so a digest that counted the stamp line would be a function of itself: write the
  stamp, the digest moves, the stamp is stale, forever. `_canon_digest` blanks that one line in every
  source first, and `selftest` asserts the digest is invariant to the stamp's value **and** still
  sensitive to every other byte; the second assertion is what stops the first being satisfied by a
  digest that ignores everything. Both directions were checked by seeding, not by watching a pass: a
  freshly rendered copy yields no finding, and one appended line in a throwaway copy of canon makes it
  stale. Seeds are excluded from the digest deliberately — a seed is written once and then belongs to
  the repository, so editing `canon/LICENSE` is not engine drift and must not age eight copies at once.
- The stamp is why nothing in this engine may write a dollar-sigil token in its own prose any more:
  the file is rendered, so a comment explaining a placeholder gets the placeholder substituted out of
  it, and the vendored copies then carry a comment asserting the opposite of the truth. Caught by
  diffing `.github/repo-docs.py` against `scripts/docs.py` after the first attempt, which had turned
  "the escape is a doubled dollar" into "the escape is a dollar" in every repository.

### Removed — `common`

- **`common` is gone from the audit.** `gh api repos/APS-Conecta/common` returns 404 and the
  repository is not archived; the organisation holds eight repositories and that is not one of them.
  Its four baseline findings and its `repo_archetypes` entry are removed by hand, exactly as
  `analizador-rem` was, so no unrelated drift rides in on a regenerated baseline. `README.md` loses it
  from the unreconciled-licence list, and the count of repositories not cloned locally goes from three
  to two — `calculadora-ecicep` and `Databases`, checked against the organisation's repository list.
  The same paragraph's other counts were measured and corrected with it: 25 rules, 5 settings probes
  and six cloned repositories, not 23, 4 and four.
  Those two uncloned repositories are deliberately **not** given baseline keys: `check` only ever keys
  the snapshot on directories the disk walk discovered, and `--save-baseline` replaces the file
  wholesale, so a hand-added key for an uncloned repository yields no findings and deletes itself on
  the next save.

### Fixed — third pass: the gate itself was wrong

- **…and once it ran, it failed three repos on a checkout layout.** `gaps()` decided whether an org
  default was present by looking for a sibling `.github` clone via `discover()`. CI has no sibling
  clone, so `common`, `epidemiologia` and `territorio` reported `CONTRIBUTING.md` and `SECURITY.md`
  missing — a verdict about the checkout, not the documentation. Inheritance is now read from the
  profile's `org_inheritable`, which is where the decision lives, and the *presence* of those files is
  verified where it belongs: `org_level` requires all five when auditing `.github` itself. Selftest now
  asserts both halves — `CODEOWNERS` is always a gap when absent because GitHub cannot default it, and
  `SECURITY.md` must never be reported missing because it is inherited.
- **The vendored CI gate could never run, in any repository.** `SKILL` was
  `Path(__file__).parent.parent`, which is right for `repo-docs/scripts/docs.py` and wrong for the copy
  every repo vendors at `.github/repo-docs.py`: there it resolved `profiles/` to `<repo>/profiles/`,
  which no repo has. `P` was therefore `{}` and every invocation died in argparse with
  `KeyError: 'levels'` **before doing any work** — so the `docs` workflow that eight repositories now
  advertise had never once executed. Not theoretical: the run on `aps-conecta-web` PR #1 failed with
  exactly that traceback. Resources now resolve from either location, canon vendors
  `.github/profiles/`, and `canon-drift` — which has no canon beside the vendored copy — prints a SKIP
  and marks the run degraded instead of comparing nothing and reporting green. Found by the adversarial
  reviewer of `aps-conecta-web`; the reported "gate after → 0 errors" had come from the *other* binary.
- **`--fix` rewrote a security claim from a probe that failed.** The `dependabot-alerts` setting
  probed with `sh(["gh","api",…])` and returned `code == 0`, so a call that never reached GitHub was
  indistinguishable from *the feature is off* — and because `--fix` rewrites a checklist box to match
  the probe, one flaky call silently edited `gestion/.github/SECURITY.md` to claim a security feature
  was **disabled while it was enabled**. Caught by watching the same box flip between two runs. The
  probe now reads the HTTP status (`204`/`200` on, `404` off, anything else **unknown**), and
  `claim-boxes` never edits a box from an unknown reading — a stale box is a smaller defect than a
  confidently wrong one. This is the third place the same root cause appeared: a failed probe must
  never be readable as an answer.
- **`dependabot-security-updates` is now its own setting.** gestion's checklist asked for "Dependabot
  alerts + security updates" on one line, while alerts were **on** and automated fixes were **off** —
  so the line could not be ticked honestly in either direction. Alerts tell you; updates open the pull
  request. Two settings, two boxes, both machine-checked.
- **The issue-form contact link pointed at a file that will never exist.** `canon/ISSUE_TEMPLATE/config.yml`
  substituted `$org/$repo/blob/main/CONTRIBUTING.md`, but ADR-0012 deliberately leaves most
  repositories without a local CONTRIBUTING — they inherit the org's. The link was dead in six of
  eight repos, laid down by `--fix` in the same pass that decided they should not have that file.
  It now points at the copy that is actually served. `canon/pre-commit` also carries its own
  executable bit now, rather than relying on the destination chmod alone.
- **`--fix` installed a hook that could never run.** `scaffold` chmods what it writes; `canon-drift`
  only wrote the text, so every `.githooks/pre-commit` it installed was **not executable** — 5 of the
  6 repositories that have one, recorded in git as `100644`, which means every clone got a dead
  secret-guard while `CONTRIBUTING.md` documented it as a gate. Mode is part of the artifact, so a
  wrong mode is now drift: `canon_executable` in the profile names which canon needs the bit,
  `--fix` sets it, and a present-but-inert hook is reported as **NOT EXECUTABLE** rather than passing
  silently. Found because git itself warned while committing in a nested clone. Asserted in
  `selftest` in both directions.
- **A degraded run may no longer be recorded as a baseline.** `gh()` returned `None` on failure and
  `fact-vs-reality` swallowed every probe exception with a bare `except Exception: continue`, so a
  flaky API call was indistinguishable from a satisfied check — and `--save-baseline` then wrote the
  loss down as *resolved*. Caught live: one `--all` run retired four real findings in `gestion`,
  including both `team_size` mismatches and the Dependabot claim box, all of which reappeared on the
  next single-repo run. Failures now collect in `DEGRADED`, the run reports them, `--save-baseline`
  refuses to write, and `--offline --save-baseline` is refused outright because CI deliberately
  evaluates a subset. The baseline exists to tell a documentation regression from a rule regression;
  it could not do that while a network hiccup looked like progress. Taught by `gestion`.
- **The licence posture is AGPL in the prose too.** `SKILL.md`, `references/conventions.md` and the
  org-default `public/CONTRIBUTING.md` still enforced ADR 0007's proprietary posture after ADR 0010
  superseded it: `d1e007a` switched the engine and left every sentence describing it. New
  **`licence-prose`** (error) — a governed doc that describes our own code as proprietary now fails,
  with the brand carve-out (marks are reserved under AGPL §7(e), correctly) and prohibitions
  excluded, since neither is a claim. Four declarations of the licence were being verified and the
  sentence next to them was not. Taught by `repo-docs` itself, which reported 0 errors while
  contradicting its own profile, and by `.github/profile/README.md` — the organisation's only
  public page, which called the code proprietary four times.
- **`discover` no longer reports an unreadable repository as an absent one.** `apps/` is chowned to
  the container uid so Nextcloud can write it, which makes host git refuse those clones as "dubious
  ownership"; every git call then failed identically to having no remote, so the repo dropped out of
  the audit and the run still exited green. `territorio` and another clone had therefore never
  been audited at all — 63 findings between them on first sight, including a `README.md` link
  broken exactly like `epidemiologia`'s. `sh()` now scopes `safe.directory` to the path it was asked
  about, and `discover` reports `unreadable` separately. Taught by `territorio` and another clone.
- **The default branch is not the checked-out branch.** `canon_vars`, the `pr` base and
  `branch-name` all read `HEAD`, so working on a feature branch — the only way `CONTRIBUTING.md`
  allows anyone to work — baked that branch's name into `docs.yml` on `--fix`, and would have opened
  a pull request against itself. New `default_branch` fact, resolved from `origin/HEAD`, then
  `origin/main` or `origin/master`, falling back to `HEAD`; `origin/HEAD` is unset in half these
  clones. Taught by this branch.
- **`doc-language` honours the deliberate exceptions.** `gestion` was reported as mixed because of
  `docs/CONVENTIONS.md`, `docs/BRANDING.md` and `themes/apsconecta/MAPEO.md`, which `AGENTS.md`
  names as deliberately Spanish, and because of a glossary *of* Spanish domain terms — reference
  material about Spanish, not documentation written in it. Which documents those are is a decision,
  so the list lives in the profile as `doc_language_exempt`. Taught by `gestion`, alongside a repo
  whose other three Spanish documents remained findings.
- **`--org` published canon that must never be public.** `canon-drift` ignored org mode, so `--fix`
  on the world-readable `.github` repository added `CODEOWNERS` — naming three accounts, two of which
  have no access to anything — plus the pre-commit hook, the docs workflow and a full copy of the
  engine. GitHub can inherit none of those regardless. A `canon_org` list now names the only four
  canon files publishable there, and `canon/CODEOWNERS` carries one owner from `code_owners` in the
  profile, since who reviews is a decision. Its comment no longer explains which review rule cannot
  be enforced. Taught by `.github`.
- **The org repository published `$PLACEHOLDER` as its CONTRIBUTING and SECURITY.** `scaffold`'s gap
  loop wrote the placeholder stub first, so the block that copies the authored documents out of
  `public/` found the file already present and never fired — dead code from the day it was written.
  Nothing caught it: an untracked file is not governed, so the placeholder was invisible to `check`
  until the commit that published it. The gap loop now prefers `public/` in org mode. Taught by
  `.github`, one commit before the world would have read it.
- **`profile/README.md` was required and undetectable.** The org level lists it among the required
  files, but `find_health` never looked for it, so `missing-required` reported the organisation's only
  document as absent while it sat in the tree. Taught by `.github`.
- **A tracked file the working tree lacks is reported, not crashed on.** `doc_lang` reads every
  governed file, so one tracked-but-deleted document — mid-rename, or a deletion not yet staged —
  ended the entire run in a traceback. New `tracked-not-present` (error), and `governed()` no longer
  returns paths that are not there.
- **The canon templates stopped assuming `gestion`.** The pull-request template asserted that
  `make test` passes "the same script `.github/workflows/ci.yml` runs", and the dev-task form
  described itself as assuming "make test/smoke fluency" and cited `AD-5` as an example reference.
  These are Mechanical files, identical across the organisation by definition, and they are served to
  a Python CLI and a PHP library that have neither a Makefile nor an `AD-` series.
- **The canon licence was still the proprietary one.** `_base.json` mapped
  `canon/LICENSE.proprietary` → `LICENSE`, so scaffolding any repository that lacked one would have
  handed it an all-rights-reserved licence *under the AGPL posture* — and `license-posture` would
  then have failed that same repository on the next run. Nothing referenced the file except the canon
  map, which is how it survived the relicence unnoticed. Canon now holds the AGPL-3.0 text itself,
  byte-identical to the one all seven code repositories ship (verified 2026-08-08), under the
  posture-neutral name `LICENSE`.
- **`orphan-reference` reads code voice, not prose.** It flags a document mentioning an app concept
  under `custom apps/` that has no repository — but "Farmacia" in `gestion/docs/CONVENTIONS.md` is an
  item in a Spanish list of clinic units (SOME, Dental, OIRS, Estadística-REM, Dirección): a pharmacy,
  not a missing repository. The engine already held the right craft for this, one rule away — *"`make
  it` in code voice is a command, 'make it' in prose is the English verb"* — so the name must now
  appear in backticks or beside a project word. Taught by `gestion`.
- **`adr-status` looks for the forward link in the paragraph, not the line.** `gestion`'s ADR-0002 is
  superseded on one half and links forward to `ADR-0000 §AD-5` — on the following line, because
  Markdown prose wraps. The rule demanded the link on the same line as the word "superseded", so a
  correctly-linked ADR was reported as unlinked. Taught by `gestion`.
- **`licence-prose` does not fire on past tense.** "our own output *was* proprietary" recounts;
  "our own output *is* proprietary" asserts. Two paragraphs of `docs/LICENSING.md` explaining the trade
  ADR-0010 made were flagged as though they were making it. Note this is the opposite call to
  `RETIRED`, where `was` was removed for matching ordinary prose: there the word had to prove a
  retirement anywhere in a sentence, here the sentence is already about our licence and tense is all
  that remains to read. Taught by `gestion`.
- **`absolute-path` no longer flags a path named as off-limits.** `AGENTS.md` has a "Do not touch"
  section whose entire purpose is to name `/srv/syncthing/CESFAMS` so that no agent writes there;
  making that path portable would have deleted the warning it exists to give. Now heading-aware.
  Taught by `gestion`.

### Fixed — fourth pass: what an independent audit of this tool found

Ten explorer agents mapped the organisation and an adversarial critic re-ran every claim. Most of what
they found was in here, not in the documentation.

- **The 2FA pre-flight failed OPEN, and ADR 0003 claimed it was asserted.** `_guard_2fa` returned
  `[m for m in str(out or "").split()]`, and `gh()` returns `None` on failure — so a request that
  never reached GitHub read as *"nobody lacks 2FA"* and the tool would have gone on to enforce it.
  Enforcing removes every member without 2FA; this organisation has **one** member. A flaky network
  could have cost the owner the organisation. It now fails closed, and `selftest` asserts both
  directions — verified by reverting the guard and watching the assertion fail. ADR 0003 said this
  was "asserted in the selftest and must never become advisory" while nothing asserted it.
- **`required()` and `public-leak` keyed on an operator flag instead of the archetype.** `check --all`
  passes one `--org` for eight repositories, so a sweep could never be right about both the org repo
  and the other seven: it demanded a `LICENSE` and `CODEOWNERS` that `references/layout.md` forbids
  there, while identifying the repo *by* the `profile/README.md` it reported missing. Worse,
  `public-leak` returned early unless `--org` — so during every `--all` run the leak rule was **off
  for the only world-readable repository in the organisation**. Both now derive from the archetype.
- **Skipped rules were counted as resolved.** An `--offline` sweep printed
  `SKIP branch-name` and `RESOLVED branch-name … default branch is 'master'` in the same run, while
  the branch was still `master`. A rule that did not run knows nothing: its prior findings are now
  reported `UNKNOWN`, never resolved, and the run is marked degraded.
- **`missing-required` ignored what the organisation actually serves.** GitHub applies the public
  `.github` repo's CONTRIBUTING, SECURITY, issue forms and PR template to every repository lacking its
  own, so demanding a local copy asked for the DRY violation the org-before-repo rule exists to
  prevent. `gaps()` now counts an org default as present, from `org_inheritable` in the profile.
  Closed roughly sixty findings that were never defects. CODEOWNERS, workflows and hooks stay
  per-repo, because GitHub cannot inherit those.
- **Dated history is no longer read as making a claim.** `_claims()` scanned CHANGELOG, BUGS, ROADMAP
  and ADRs, so the changelog entry *retiring* the three-person team — which has to quote
  `"as fast as a 3-person team can"` in order to retire it — was itself reported as a contradiction.
- **`licence-prose` exempts the notices document,** which exists to reproduce other people's licence
  text, much of it reserving rights over work that is not ours.
- **The nested-repo boundary tested only the first path segment.** All three app clones live at
  `apps/<id>`, so `r.split("/")[0]` asked whether `apps/.git` existed. It does not, and the boundary
  held by luck alone: gestion tracks nothing under `apps/`. `CONTEXT.md` promises it unconditionally.
- **New `github-metadata` (error).** A repository description is the most-read documentation it has —
  it appears in every list, every search result and on the organisation's front page — and nothing
  governed it. On first run: three descriptions presumed a single clinic, two were Spanish under an
  English-docs policy, and `territorio` had none at all. Taught by the whole org at once.

### Removed — third pass

- **`licence-copyleft`.** It asked whether copyleft dependencies were safe under a *proprietary*
  posture; ADR 0010 made the organisation AGPL-3.0-or-later, so its first line returned before the
  rule could ever fire again. The question that would replace it — is a dependency *incompatible*
  with AGPL-3.0-or-later, GPL-2.0-only being the one that bites — cannot be asked of `inventory()`,
  which resolves licences to coarse families: `gpl` alone does not say whether an "or later" option
  exists to take. Rather than leave a rule that cannot fire, or document a check that cannot run,
  both are gone and `SKILL.md` now says explicitly that nothing checks it. A comment at the deleted
  site records what it would take to bring it back. Its `copyleft` profile table went with it, read
  by nothing once the rule was removed.

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
- 16 rules and 5 facts, seeded from defects found in `gestion`, `epidemiologia` and `territorio`.
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
- `license_kind` had no AGPL branch, so `epidemiologia` reported the vague
  `other` instead of the real finding: it ships **AGPL-3.0**, which ADR 0007 requires reconciling.
  Taught by `epidemiologia`.
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
