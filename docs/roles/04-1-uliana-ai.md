# Role 4.1 — Uliana: Agent orchestration

**Deliver by September 11:** one bounded, inspectable agent workflow that connects context, history, meals, product matching and optimization into the shared result.

Implement orchestration in Python inside the backend service. Call the other authors' Python modules directly and return validated data through Rina's HTTP API to Next.js. Coordinate background plan execution with Rina so progress polling remains responsive.

Read [Product](../PRODUCT.md), [Contracts](../CONTRACTS.md) and [Integrations](../INTEGRATIONS.md).

## Implement this workflow

1. Validate the request and retrieve Arina's user/cart context. Resolve shared household restrictions according to the product rules.
2. Retrieve history when recurring analysis is enabled; ask Vika for suggestions. Empty history is a valid input.
3. Ask Sofiia for a meal plan and normalized ingredients using the confirmed constraints.
4. Ask Rina for real product candidates and unresolved matches.
5. Ask Vika to calculate the basket and choose suitable alternatives. Request additional candidates from Rina if needed.
6. If justified, request at most one revised meal plan from Sofiia, preserving restrictions and portions; then rematch and recalculate. Use the bounded pass limits in the contract.
7. Validate and assemble `PlanningResult`, including sources, warnings, totals and whether confirmation is allowed. Return it through Rina's run API.

Cart writes happen through Rina's separate confirmation route. The planning agent returns a proposal; it does not add products while planning.

## Your implementation responsibilities

- Agent state and module calls, LLM prompts/tool definitions if used, structured output validation and short progress events.
- Explicit failure/degraded behavior: missing history, invalid provider output, unavailable meal service, unresolved products and impossible budget.
- A recalculation entry point for Rina: retain confirmed constraints and the user's selected recurring IDs, refresh candidates/costs, and return a new run/result without silently resetting selections.
- Bounded calls/timeouts; no endless optimization loops or accidental repeated provider requests.
- Deterministic validation around model outputs. Real product IDs/prices must come from catalog data; arithmetic comes from Vika's module.
- A source label for every fallback. No private model reasoning, raw secrets or misleading completion messages in progress events.

## Add these files/results

- `services/api/src/smart_basket/agent/`: orchestration, state, prompts/configuration and result assembly.
- `fixtures/planning-result.json` and `fixtures/run-failed.json`, assembled from the shared synthetic module fixtures.
- A small developer entry point or documented command that runs the complete pipeline with injected mocks.
- Model-provider environment variable names for Rina and `docs/handoffs/uliana.md` with call order, limits, failure rules and checks.

## Independence, dependencies and dates

| Date | Your output / dependency |
|---|---|
| 6th | Agree Python module interfaces and background plan execution with Rina; confirm JSON output with Ksiusha and choose the team's model/provider setup |
| 7th | Receive Arina/Sofiia/Vika/Rina signatures and fixtures; deliver a complete mock pipeline and result to Rina/Alina |
| 8th–9th | Replace mocks with real modules one at a time and run the developer compatibility flow with Rina |
| 10th–11th | Check bounded retries/replan, bad outputs and impossible constraints; merge and hand off |

You can start immediately with injected mock functions. Only a full live pass depends on real module implementations. Before September 12 you coordinate AI blockers yourself with Sofiia, Vika and Rina; Polina is not an early dependency.

## Done means

- [ ] One command/API request runs the full workflow and produces schema-valid output.
- [ ] Output is personalized from actual inputs/context, not a fixed paragraph.
- [ ] Progress describes calls actually completed; all runs reach completion or a useful failure.
- [ ] Model output cannot bypass constraints, invent prices or trigger cart writes.
- [ ] Optimization/replanning limits work and infeasibility is visible.
- [ ] Rina's API serves the result and Alina can render it before September 11 ends.
- [ ] Handoff distinguishes working live steps from mocks and explains how to reproduce both.

## Added scope: Edamam + FatSecret

Keep Edamam in the planning pipeline. Preserve Sofiia's per-meal quantities and plan versions so Rina can build a separate export preview. Coordinate the handoff/check by September 9; finish by September 11. FatSecret saving runs only after the user's separate confirmation, outside automatic planning. Expose availability/errors without failing the main plan when FatSecret is unavailable. Follow [the combined workflow](../FATSECRET.md).
