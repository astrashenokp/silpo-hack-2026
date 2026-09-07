# Role 3.1 — Arina: Silpo MCP connection and read layer

**Deliver by September 11:** an authenticated, reusable MCP gateway and clean context/history/catalog data for the other modules.

Implement your adapters and OAuth routes in Python within the shared backend service. Rina and the AI authors consume your Python interfaces. With Ksiusha, verify that the Next.js API forwarding preserves the public OAuth redirect/session behavior.

Read [Integrations](../INTEGRATIONS.md), [Contracts](../CONTRACTS.md) and the linked official MCP documentation.

## Implement in this order

1. By September 6, test access with the authorized demo account. Discover actual tool names/input schemas and record what is available. Identify required store/cart context and access blockers immediately.
2. Implement server-side MCP connection and the web application's OAuth/session flow. Own auth routes, callback validation and session isolation. A login in a separate AI client is only an access experiment, not your finished web integration.
3. Implement read adapters for user/profile context, family/restrictions when available, online/offline purchase history and receipt items. Normalize their data into the shared types.
4. Implement low-level product search, product details, promotion reads and current cart/context reads. Rina will reuse these to match ingredients and change the cart.
5. Normalize provider failures: authorization needed, missing context, rate limit, unavailable service and malformed response. Use bounded retries for safe reads and useful diagnostics without sensitive payloads.
6. Expose one authenticated gateway for Rina's permitted action wrappers. Keep action policy in Rina's module; do not create a second cart workflow here.

## Add these files/results

- `services/api/src/smart_basket/mcp/`: connection, auth/session support and normalized read adapters.
- Auth handlers in `services/api/src/smart_basket/routes/`, coordinated with Rina.
- `fixtures/user-context.json` and `fixtures/purchase-history.json`, including empty-history/missing-field variants. Use synthetic identities and receipts.
- Provider setting names for Rina's `.env.example`; no tokens or personal records.
- `docs/handoffs/arina.md`: live access evidence, tool-to-wrapper mapping, required context, history coverage, normalization choices, run instructions and known gaps.

## Dependencies and handoffs

| Date | Give this | To |
|---|---|---|
| 6th | Access result and known context requirements | Rina + Uliana; Ksiusha for connection UI |
| 7th | Wrapper signatures and synthetic context/history/catalog examples | Rina + Uliana + Vika |
| 8th–9th | Live read gateway and working web auth route | Rina + Uliana + Ksiusha |
| 11th | Verified adapters and complete secure setup instructions | Rina's combined handoff; Polina reads it on 12th |

Start normalization, mocks and error behavior independently. Real provider verification must wait for an authorized session and valid context. If access is blocked, tell Rina/Uliana that day and continue the adapters; do not mark mock responses as live. You do not depend on meal planning or Figma.

## Done means

- [ ] Real authenticated reads work from our backend, with a documented setup process.
- [ ] Context/history/catalog output matches the shared types; consumers never parse raw MCP shapes.
- [ ] Empty history and unavailable profile fields are distinguished from provider failure.
- [ ] Pagination/history coverage and reliable deduplication keys are documented.
- [ ] Existing cart/store context can be read and validated; missing context produces a usable error.
- [ ] Rina can reuse the connection instead of implementing another OAuth client.
- [ ] Expired-session and timeout paths have been checked; logs and fixtures contain no personal secrets.

You supply purchase data, not recurrence predictions. You supply catalog reads, not the product-matching or budget algorithm.

## Added scope: Edamam + FatSecret

Own `services/api/src/smart_basket/fatsecret/auth.py` and `client.py`: OAuth 1.0 authorization for the existing user account, isolated token storage and signed provider transport. Check account access by September 8 and give Rina a usable client; finish by September 11. Give Ksiusha the connection status/start/callback contract. Record actual app-account linkage, not merely creation of an API-only profile. Follow [the combined workflow](../FATSECRET.md).
