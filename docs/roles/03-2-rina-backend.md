# Role 3.2 — Rina: API, product matching and cart actions

**Deliver by September 11:** the shared HTTP interface, product-candidate workflow and confirmed cart operations. You also coordinate initial backend/shared setup and the combined developer handoff because Polina starts only on September 12.

Read [Contracts](../CONTRACTS.md), [Workflow](../WORKFLOW.md) and [Integrations](../INTEGRATIONS.md).

## Implement in this order

1. By September 6, configure the Python service and agree the JSON contract with Ksiusha and Uliana. Document the Python HTTP framework, dependency setup and launch commands, create the application entry point and agree Next.js API forwarding with Ksiusha. Do not defer setup to Polina.
2. Expose the documented HTTP routes with fake context/planner/cart implementations so frontend work can start. Own run storage and session-scoped access. Connect Uliana's worker to run snapshots/progress.
3. Build ingredient-to-product matching using Arina's search/details adapters: query terms, candidate retrieval, availability/composition checks, package/unit normalization and unresolved matches.
4. Implement alternative lookup for unavailable/expensive products. Return candidates and evidence to Vika; Vika chooses the optimized selection and computes totals.
5. Build cart preview against the existing cart and the current plan version. Recheck price/availability/context, preserve unrelated items and explain what will change.
6. Implement confirmation, per-item outcomes, duplicate-request protection and read-back verification after uncertain failures. Add/update/remove wrappers only as required by reviewed changes; no checkout/payment flow.
7. Replace mocks with Arina's gateway and Uliana's planner. With Ksiusha/Alina, exercise the main developer flow by September 9. Collect the exact final revision, commands and handoffs by September 11.

## Add these files/results

- `services/api/src/smart_basket/catalog/`, `cart/`, and HTTP handlers in `routes/`.
- `packages/contracts/`: language-neutral JSON schemas; coordinate matching frontend types with Ksiusha.
- `services/api/src/smart_basket/schemas/`: Python validation and explicit camelCase JSON serialization.
- `services/api/pyproject.toml`: dependencies/package setup, plus a documented Python application entry point and environment setup.
- Backend/root launch configuration and `.env.example` using actual variable names.
- `fixtures/product-candidates.json`, `cart-preview.json`, `cart-partial.json`; coordinate schema validation of all fixtures.
- `docs/handoffs/rina.md`: API usage, cart behavior, verification and remaining limitations.
- `docs/handoffs/integration-ready.md`: shared revision, complete launch commands, modules/owners, live versus mocked services, fixture access, environment/access procedure and known bugs. This is Polina's September 12 entry point.

## Independence and dated inputs

- Start HTTP routes, validation, matching and cart-state logic against a fake gateway immediately.
- Receive Arina's schema/context report by September 6, wrapper examples by 7th, and live gateway around 8th.
- Receive Sofiia's ingredient examples and Vika's optimizer signature by 7th. Resolve unit/package mismatches together before live integration.
- Receive Uliana's orchestration interface by 7th and working pipeline around 8th–9th.
- Provide mock API/fixtures to both frontend developers by 7th and live methods by 8th–9th.
- Complete and merge by 11th. Polina takes final integration on 12th; you support fixes on 12th–13th.

## Done means

- [ ] HTTP requests/results/errors match the shared contract and reject invalid or cross-session data.
- [ ] Candidate quantities represent actual purchasable units; missing conversion data stays unresolved.
- [ ] Unsuitable/unknown products are not silently treated as safe matches.
- [ ] Planning and optimization do not mutate the real cart.
- [ ] Preview identifies exact additions, current contents and totals; changed state requires re-review.
- [ ] Repeated confirmation cannot duplicate items; partial/uncertain writes are reconciled and reported.
- [ ] Synthetic IDs cannot reach live writes; unrelated existing cart items are preserved.
- [ ] Both frontend developers and Uliana can exercise their interfaces before your final handoff.
- [ ] Polina can start the delivered revision from written instructions without needing you to invent missing setup steps.
