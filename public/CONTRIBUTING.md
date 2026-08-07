# Contributing — $org

Organisation-wide contribution contract. It applies to every `$org` repository unless that
repository ships its own `CONTRIBUTING.md`, which takes precedence.

The repositories themselves are private. This file is public because GitHub only serves
organisation defaults from a public `.github` repository.

## Workflow (GitHub Flow)

1. Branch off the default branch, short-lived: `feat/…`, `fix/…`, `docs/…`, `chore/…`.
2. Commit with [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`,
   `docs:`, `chore:`, `test:`, `refactor:`.
3. Open a PR. **One human approval before merge.** This gate is team convention — GitHub's free
   plan does not enforce branch protection on private repositories — so respect it rather than
   rely on it.
4. AI-assisted PRs are labelled `ai-assisted` and disclose the involvement in the description.
5. Run the repository's own gate before opening the PR. CI runs the same checks.

`CODEOWNERS` auto-requests reviewers. Prefer small, reviewable PRs.

## Issues

File new work with the templates in `.github/ISSUE_TEMPLATE/` — a technical *Dev task/bug* and a
plain-language *Solicitud*. Use the plain-language form when you are describing a need rather than
a diagnosis; translating it into technical terms is the developer's job, not yours.

## Documentation rules

Documentation must let someone **rebuild** the system, not just read about it.

1. Numbered steps, one action each — the exact copyable command.
2. Every step states its expected output and what to do if it fails. A step you cannot verify is
   not a step.
3. Every command says where it runs — the host, or which container and as which user.
4. Never assert what you have not run. If it is untested, the document says so *there*, not in a
   preface.
5. One owner per fact. Others link; they do not repeat. A second copy desyncs the day it is written.
6. Prefer generated over hand-written.
7. Do not copy a gate's count into prose — say what the gate proves and let it print the number.

If a document mentions something retired, it must acknowledge that it is. Dated history — ADRs,
changelogs — is exempt; its date is the label.

## Decisions

Architectural decisions are recorded as ADRs under `docs/adr/`, numbered sequentially from `0001`,
following [MADR](https://adr.github.io/madr/). `Status:` is mandatory. Superseded ADRs stay in place
and link forward — a deleted ADR is a deleted reason.

## Licensing

Everything `$org` produces is **proprietary, all rights reserved**. The dependencies it builds on
are open source and self-hosted. Contributions are accepted on that basis. Do not add an
open-source licence file to a repository, and do not describe this organisation's own code as open
source.

## Security

Do not open a public issue for a security problem. See [`SECURITY.md`](SECURITY.md).
