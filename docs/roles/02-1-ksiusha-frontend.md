# Role 2.1 — Ksiusha: Input form and page shell

**Deliver by September 11:** a working planning page shell that collects valid user parameters, launches a plan and supplies its state/results to Alina's components.

Read [Product](../PRODUCT.md), [Contracts](../CONTRACTS.md) and [Workflow](../WORKFLOW.md).

## Implement in this order

1. With Rina and Uliana, configure the confirmed Next.js + Python stack and shared JSON contract by September 6. Create the Next.js frontend, document its install/start commands and agree `/api/...` forwarding to Python with Rina. You own frontend setup; do not wait for Polina.
2. Build the page shell and shared state: current form, connection/context state, current run, loading/failure and active result. Coordinate a single state owner with Alina.
3. Build budget, days, people, calories, preference/restriction controls, pets and recurring-analysis toggle. Add optional notes only if the main form is complete.
4. Add field validation and useful labels. Convert UAH to integer kopiykas exactly once. Clearly explain that the MVP uses shared household dietary constraints.
5. Add account connection and profile/context summary using Arina's auth/context contract. Let the user review form values before starting; do not silently overwrite edits with late profile responses.
6. Implement one API client with interchangeable mock/live configuration. Submit `PlanningRequest`, retain `runId`, poll `RunSnapshot`, and stop on completion/failure/unmount. Ignore responses belonging to an older run after a new run starts.
7. Mount Alina's components and pass current snapshot/result plus callbacks. Apply Katia's final styles after September 7 and verify desktop/mobile behavior.

## Add these files/results

- Next.js scaffold and `apps/web/src/app/`: layouts, page and interactive planner state.
- `apps/web/src/features/planner-input/`: form, context summary and validation.
- `apps/web/src/lib/api/`: client and TypeScript types matching the shared JSON schemas; coordinate Alina's result/cart methods here. Check camelCase JSON against Python serialization.
- `fixtures/planning-request.json`: golden input matching the executable schema.
- Frontend launch/environment instructions and `docs/handoffs/ksiusha.md`.

These are the proposed paths in [Workflow](../WORKFLOW.md); record any agreed path changes there.

## What you receive and give

| Dependency | Available when | Your response |
|---|---|---|
| Katia's draft/final Figma | 6th / 7th | Build behavior first, then final styling |
| Rina's HTTP types and mock route | 6th–7th | Use them immediately; request schema changes explicitly |
| Sofiia's supported food filter labels | By 7th | Use supported labels and human-readable display text |
| Arina's live connection/context | 8th–9th | Replace mock context and verify sign-in states |
| Alina's results | Mock components by 7th | Connect through shared page state and callbacks |

You can implement every form and loading/error behavior with fixtures. Only final styling and live verification depend on later inputs. Give Alina the shell/component interface by September 7 and Rina a valid request example. Deliver your complete handoff by September 11; Polina first uses it on September 12.

## Done means

- [ ] Form submits exactly the documented request; invalid values are blocked and backend errors are displayed.
- [ ] Preference and restriction selections survive loading/re-rendering.
- [ ] Account-not-connected, missing-context and expired-session states are understandable.
- [ ] Duplicate clicks do not create accidental simultaneous runs.
- [ ] A completed or failed run stops polling and displays the correct current state.
- [ ] Form → Alina's results works on mocks and the available real API by September 11.
- [ ] Layout works on desktop/mobile and can be operated with the keyboard.

Alina owns result presentation; Rina owns server validation/API; Arina owns OAuth. Do not implement provider secrets or direct MCP calls in the browser.

## Added scope: Edamam + FatSecret

Add FatSecret connection status and the Connect action to Next.js, using Arina's separate authorization flow. Coordinate export client types with Alina and Rina. Mock the v0.2 connection/preview contracts by September 8; finish by September 11. A disconnected FatSecret account must not block planning or the Silpo flow. Follow [the combined workflow](../FATSECRET.md).
