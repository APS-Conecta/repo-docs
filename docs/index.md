# Documentation

One table, one row per governed document — the standard shape `references/layout.md` defines and
`estadistica/docs/index.md` exemplifies.

| Document | Mode | Reader | It is the authority for |
|---|---|---|---|
| [`README.md`](../README.md) | reference + how-to | anyone meeting the tool | what this is and is not, the quickstart, every command |
| [`CONTEXT.md`](../CONTEXT.md) | reference | contributors | the vocabulary — read it before changing anything |
| [`CONTRIBUTING.md`](../CONTRIBUTING.md) | how-to | contributors | how to add or delete a rule |
| [`SECURITY.md`](../SECURITY.md) | reference | anyone reporting an issue | scope, the private reporting channel, what is out of scope |
| [`CHANGELOG.md`](../CHANGELOG.md) | reference | contributors | the tuning log — every false positive this tool has produced, and its fix |
| [`SKILL.md`](../SKILL.md) | reference | the agent invoking the skill | how the skill is loaded, switched and run |
| [`docs/adr/0001`](adr/0001-mechanical-and-judgment-are-separate-classes.md) | explanation | contributors | why mechanical and judgment are separate classes, and seeds are neither |
| [`docs/adr/0002`](adr/0002-craft-in-the-engine-decisions-in-a-profile.md) | explanation | contributors | why craft lives in the engine and decisions in a profile |
| [`docs/adr/0003`](adr/0003-the-tool-changes-github-settings.md) | explanation | contributors | why a documentation tool changes GitHub settings, and what fences the irreversible one |
| [`docs/adr/0004`](adr/0004-the-checker-is-vendored-into-every-repo.md) | explanation | contributors | why the checker is vendored into every repository |
| [`docs/adr/0005`](adr/0005-one-published-surface.md) | explanation | contributors | why REST is the one published surface for cross-app reads |
| [`references/layout.md`](../references/layout.md) | reference | contributors | file trees per level, GitHub's health-file precedence, org-versus-repo rules |
| [`references/conventions.md`](../references/conventions.md) | reference | contributors | Diátaxis, Keep a Changelog, MADR, style, language policy, licence posture, citation doctrine |
| `docs/index.md` | reference | readers | this map — what to read, and what is deliberately not here |
| [`canon/`](../canon/) | reference | contributors | the canon every vendored copy is rendered from; `canon-drift` enforces it |
| [`public/`](../public/) | reference | contributors | the subset publishable to the world-readable org repository |
| [`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md) | reference (generated) | PR authors | the pull-request checklist, rendered from canon |

## What is not here

There is no tutorial. The quickstart in the README is four commands and covers the whole tool; a
tutorial would be a second copy of it, and second copies desync the day they are written.
