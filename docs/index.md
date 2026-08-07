# Documentation

## Start here

- [`README.md`](../README.md) — what this is, how to run it
- [`CONTEXT.md`](../CONTEXT.md) — the vocabulary. Read before changing anything
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — how to add or delete a rule
- [`CHANGELOG.md`](../CHANGELOG.md) — every false positive this tool has produced, and its fix

## Decisions

- [ADR 0001](adr/0001-mechanical-and-judgment-are-separate-classes.md) — mechanical and judgment are
  separate classes, and seeds are neither
- [ADR 0002](adr/0002-craft-in-the-engine-decisions-in-a-profile.md) — craft lives in the engine,
  decisions live in a profile
- [ADR 0003](adr/0003-the-tool-changes-github-settings.md) — a documentation tool changes GitHub
  settings, and what fences the irreversible one

## Reference

- [`references/layout.md`](../references/layout.md) — file trees per level, GitHub's health-file
  precedence, org-versus-repo rules
- [`references/conventions.md`](../references/conventions.md) — Diátaxis, Keep a Changelog, SemVer,
  MADR, badges, language policy, licence posture

## What is not here

There is no tutorial. The quickstart in the README is four commands and covers the whole tool; a
tutorial would be a second copy of it, and second copies desync the day they are written.
