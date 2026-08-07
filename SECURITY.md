# Security policy — repo-docs

## Scope

A documentation tool for this organisation's own repositories. It holds no patient or clinical data
and processes no runtime input: it reads Markdown and repository metadata from disk and from the
GitHub API.

The repository is private. This policy exists because the tool holds more authority than a
documentation tool usually does.

## What this tool can do

It runs with the operator's own `gh` credentials, which carry `repo` and `admin:org`. Under
`--apply-settings` it changes organisation and repository settings, not only documentation
([ADR 0003](docs/adr/0003-the-tool-changes-github-settings.md)).

That is a deliberate expansion of blast radius, and it is fenced:

- Settings change **only** under an explicit `--apply-settings`. `--fix` never touches them.
- `org-2fa` refuses while any member lacks 2FA, because enforcing it removes those members — and
  this organisation has one member, who is also its owner.
- `--fix` writes only the mechanical class. It never rewrites prose, and never restores a seed
  (`LICENSE`, `CHANGELOG.md`), because restoring one destroys accumulated content.
- `pr` opens draft pull requests only, commits documentation paths only, and refuses on a working
  tree containing anything else. It never merges, force-pushes, or touches the default branch.

`selftest` asserts these paths. Treat a change that weakens one of them as a security change, not a
refactor.

## Handling of credentials

The tool stores no credentials. It shells out to `gh`, which uses the operator's existing login.
It never writes tokens to disk and never echoes API responses containing them.

`config.json` holds a filesystem path and is gitignored. Nothing else is machine-local.

## Reporting a vulnerability

Do not open a public issue. Use GitHub's private reporting on this repository, or contact the
maintainer through the [organisation profile](https://github.com/APS-Conecta).

Reports about the guard rails above are the ones worth sending — particularly any path that lets
`--fix` or `pr` write outside the documentation surface, or that gets a setting applied without the
explicit flag.

## Out of scope

- The tool trusts the repositories it is pointed at. It is not a sandbox and does not defend against
  hostile Markdown; every repository it reads is one we wrote.
- `gitleaks`, when installed, is invoked as an external scanner. Its findings and its false
  negatives are its own.
