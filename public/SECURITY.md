# Security policy — $org

Organisation-wide policy. It applies to every `$org` repository unless that repository ships its
own `SECURITY.md`, which takes precedence.

## Scope

`$org` builds internal-operations software for Chilean CESFAMs (primary-healthcare centres):
documents, coordination and team processes. Each install serves one establishment, named in that
install's configuration; the software itself names none.

**These systems hold no patient or clinical data.** Development uses synthetic fixtures only. They
are not clinical or patient-record systems, and are not intended to become one.

The code repositories are private. Only this organisation profile is public.

## Reporting a vulnerability

**Do not open a public issue for a security problem.**

Report privately through GitHub's **Report a vulnerability** button on the affected repository
(Security → Advisories). If you cannot reach the repository — it is private and you are not a
member — report it through the contact on the [organisation profile](https://github.com/$org).

Please include what you did, what happened, and what you expected. A proof of concept helps.
We acknowledge reports as fast as a very small team can, and we will tell you honestly if a fix
will take a while.

## Out of scope

Reports about the following will be closed as intentional:

- Findings against a **local development stack** — it is bound to loopback, runs synthetic data,
  and is deliberately convenient rather than hardened. It is not a deployment.
- Vulnerabilities in third-party open-source components, unless our configuration is what makes
  them exploitable. Report those upstream; tell us too, and we will track the update.
- Missing hardening on repositories that are private and have no external surface.

## Disclosure

We ask for coordinated disclosure: give us a chance to ship a fix before publishing. We will credit
you unless you ask us not to.
