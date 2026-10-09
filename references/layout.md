# Layout

## Health-file lookup, in order

GitHub resolves each community health file by walking, per repo:

1. `.github/`
2. repo root
3. `docs/`

If none exists, it falls back to the org's **public** `.github` repo, same order. Repo-local always
wins. Put health files in `.github/` so the root stays scannable.

## Defaultable at org level

`CONTRIBUTING.md` · `SECURITY.md` · `CODE_OF_CONDUCT.md` · `GOVERNANCE.md` · `SUPPORT.md` ·
`FUNDING.yml` · issue and PR templates + `config.yml` · discussion category forms.

**`LICENSE` cannot be defaulted.** It must exist per repo, so it is included when a project is
cloned, packaged or downloaded. `CODEOWNERS` is not a documented default either.

The org `.github` repo **must be public**. Everything placed there is world-readable regardless of
the visibility of the repos it serves.

## Repo tree — level `full`

```
README.md
LICENSE
CHANGELOG.md
.github/
  CONTRIBUTING.md
  SECURITY.md
  CODEOWNERS
  PULL_REQUEST_TEMPLATE.md
  ISSUE_TEMPLATE/{dev-task.yml,owner-task.yml,config.yml}
  workflows/docs.yml
  repo-docs.py
.githooks/pre-commit
```

Level `full` ships no `docs/` subtree: navigation is the README's job, not a generated index.
The README's **Documentación** section is the map — the `readme-sections` contract requires and
orders it — and the governed documents are named from there. Each page carries its own mode in
front matter (`tipo:`), values from the Diátaxis quadrants, so the mode discipline lives in the
page instead of a four-column table maintained in parallel; `diataxis-verification` reads that
typing, and a repo opted into `site-structure` (`.github/site-structure`) owes the full front matter
and the H2 skeleton its profile names per type. The rules own the teaching; this section only says where navigation lives.

Level `ultra` adds `docs/adr/` with statuses, archetype reference stubs, and the Diátaxis split:

```
docs/
  tutorials/     learning-oriented   (study + practice)
  how-to/        task-oriented       (work  + practice)
  reference/     information         (work  + theory)
  explanation/   understanding       (study + theory)
```

The split is defined but enforced by nothing: `required()` reads only the file list, so an `ultra`
repo is checked for `docs/adr` and nothing says its task guides live under `docs/how-to/`. That is
deliberate YAGNI — no repository runs `ultra` today, and until one does, the mode table carries the
Diátaxis discipline.

## Org tree — `APS-Conecta/.github`, `--org`

```
profile/README.md          bilingual ES/EN, the org's public face — preserved, never regenerated
CONTRIBUTING.md            public contract only
SECURITY.md                scope + how to report + what is out of scope
.github/
  PULL_REQUEST_TEMPLATE.md
  ISSUE_TEMPLATE/{dev-task.yml,owner-task.yml,config.yml}
```

No `LICENSE`. No hardening checklist. No vault names, bind addresses, host paths or contributor
names — the `public-leak` rule fails the run if any appear.

## Archetypes

Inferred from stack markers. Decides which README sections are required beyond the core
(what · status · quickstart · licence). Presence is checked, never order.

| archetype | detected by | extra sections |
|---|---|---|
| `app` | `compose.yaml` | deploy, config |
| `nextcloud-app` | `appinfo/info.xml` | install, config |
| `website` | `functions.php` | build, content |
| `library` | fallback | install, api, consumers |
| `org-profile` | `profile/README.md` | — (bilingual instead) |

A section counts if it appears as a heading, a bold lead-in, or a file-map table row — `gestion`
states its status in a blockquote and its licence in a table cell, and both are legitimate.

## Repo identity

Always from `git config --get remote.origin.url`, never the directory name. `custom apps/Territorio`
is the repo `territorio`. Directory names also carry accents the repo names do not
(`Epidemiología` vs `epidemiologia`) — comparisons normalise.

## Nested repos

`epidemiologia` is a git repo inside `gestion/apps/` with no `.gitmodules`. `scan` halts the walk at
any nested `.git`, so its files are never attributed to the parent and `--fix` never writes across
the boundary. Reported as `nested-repo` (info) — the tool does not restructure working trees.
