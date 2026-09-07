# Handoff: Rina — first mock API and product matching

- Date: September 7, 2026.
- Revision: local working-tree implementation; no PR or shared commit yet.
- Receivers: Ksiusha, Alina, Uliana, Vika; Arina for provider adapter boundaries.
- Status: ready for local mock integration; live integration remains incomplete.

The Python API accepts the shared planning input, returns 202, stores progress and
results per demo cookie session, and supports versioned recalculation. Cart and
FatSecret preview/confirmation flows supply success, partial and failed outcomes.
One OpenAPI contract and the required generated examples are available now.

Use [backend setup and API examples](../../services/api/README.md) for exact install,
launch and verification commands. [Fixture guide](../../fixtures/README.md) lists
the files each teammate needs. [Contracts](../../packages/contracts/README.md)
explains generation and frontend type ownership.

Main code: `services/api/src/smart_basket/` (`app.py`, `routes/`, `schemas/`,
`catalog/`, `cart/`, `fatsecret/`). `demo.py` contains temporary replacements for
unfinished team modules. No provider credentials are required. Supported environment
variables: `SMART_BASKET_MODE`, `SMART_BASKET_CORS_ORIGINS`; see `.env.example`.

Current verification: 42 passing tests covering strict validation, arithmetic,
restriction evidence, session isolation, worker failures, stale previews, parallel
duplicate cart confirmation, partial outcomes, personal portions, duplicate export
protection and fixture schema validation. Dependency deprecation warnings originate
from Starlette's HTTPX test adapter and AnyIO alias; they do not fail the checks.

Known limitations: process-local state, one worker, demo session instead of OAuth;
no live writes, timeout recovery, nutrition/recurrence optimization, pet demand,
Edamam export permissions or FatSecret app verification. The first menu is invented
and intentionally warns that it is not nutritionally complete. Nonempty recurring
candidate lookup awaits Vika's input contract. Do not treat this as final delivery.

Next connections: Arina supplies normalized catalog/context and authenticated provider
clients; Uliana supplies the planner object; Sofiia supplies real meal quantities;
Vika supplies optimization and recurring demand; Ksiusha adds the Next.js forwarder
and TypeScript types; Alina checks the mock scenario fixtures and endpoints.

Receiving teammate verification: pending. No messages have been sent on their behalf.
