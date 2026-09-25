# ADR 0005: One published surface — REST

## Status
Accepted (2026-09-25)

## Context
Territorio exposes cross-app reads through DI injection (RegistryService,
territorio ADR-0014) and declares REST the published surface (territorio
ADR-0020). Epidemiología exposes a single read-only OCS route keyed by source
(epidemiología ADR-0006). Two designs for the same need; consumers cannot
tell which is the contract.

## Decision
REST is the org's single published cross-app surface. OCS routes are
REST-shaped and conform. Each app publishes its readable surface as versioned
REST routes in its own openapi.json. DI injection remains an internal
implementation detail of the host — never a published surface. No app may
call another app's internal (non-REST) services.

## Consequences
- ApiContractTest (the farmacia pattern, farmacia L2-10) runs in every app
  that exposes public endpoints: territorio and epidemiología carry it; any
  app that grows a route adds one.
- New cross-app needs start as a route in the owning app's openapi.json, not
  a new channel.
- RegistryService stays; it stops being documentation-level contract language.
