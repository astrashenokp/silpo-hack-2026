# Role 2.2 — Alina: Results, progress and basket UI

**Deliver by September 11:** understandable planner results and a complete review/confirmation flow for adding approved products to the Silpo cart.

Build these components inside Ksiusha's Next.js application. Use the shared JSON client to call Python; keep result calculations and cart operations in the Python backend.

Read [Product](../PRODUCT.md) and [Contracts](../CONTRACTS.md).

## Implement in this order

1. Build independent components using synthetic result fixtures: progress, meal cards, ingredients, recurring suggestions, selected products, substitutions and budget summary.
2. Show meals by day and breakfast/lunch/dinner. Include servings, available calorie estimates, ingredient details and recipe source/attribution from Sofiia's output. Do not invent recipe instructions when only a source link is available.
3. Show recurring suggestions with reasons and include/exclude controls. Selection changes require “Recalculate basket”; do not locally fake a final server-approved total.
4. Show purchased package/quantity units, line totals, full basket cost and budget remaining. Display savings only when supplied with a valid baseline. Label excluded delivery costs.
5. Implement loading, empty history, incomplete matching, over-budget, failure and demo/mixed-source states. The interface must not label an incomplete result as a complete ready basket.
6. Implement cart preview and confirmation using Rina's endpoints. Show existing versus added contents and quantities. Display per-item success/partial/failure results and stale-price/context instructions.
7. Connect components to Ksiusha's shared page state; apply Katia's final Figma and verify mobile layout.

## Add these files/results

- `apps/web/src/features/planner-results/`: progress, meals, ingredients, restocking, products, budget and cart components.
- Result/cart client methods in the shared `apps/web/src/lib/api/`, coordinated with Ksiusha.
- A simple fixture-driven component/demo view covering normal, empty, failed, over-budget, incomplete and partial-cart states.
- `docs/handoffs/alina.md` with screenshots if useful, verification steps and remaining limitations.

## Independence, dependencies and dates

| Date | Your work / handoff |
|---|---|
| 5–6 | Start all result states from the contract; use small temporary synthetic examples |
| 6–7 | Receive Figma from Katia and shell interface from Ksiusha; provide mountable result components by 7th |
| 7 | Receive complete result fixture from Uliana and preview/partial-cart fixtures from Rina |
| 8–9 | Connect live results and cart methods; report mismatches directly to their owners |
| 10–11 | Complete failure/recalculation/confirmation checks; merge and hand off |

Do not wait for real prices or completed AI to build the UI. Final live verification needs Uliana's assembled result through Rina's API. Coordinate September 6–11 directly with those developers; Polina begins September 12.

## Done means

- [ ] All documented result fields are shown where useful; missing optional nutrition/savings is handled without made-up values.
- [ ] Users can distinguish selected restocking items, meal goods and suggestions.
- [ ] Changing selected restocking items invalidates old confirmation until recalculation finishes.
- [ ] “Confirm” is disabled for unresolved, stale or unapproved proposals.
- [ ] Double-clicking/retrying confirmation reuses the same operation key and does not trigger a new addition.
- [ ] Partial write failures are visible; the interface never reports full success for them.
- [ ] Source links, attribution, demo labels and goods-only budget labels are present.
- [ ] Components work inside Ksiusha's page on desktop and mobile.

Rina/Vika own numerical truth and cart operations. Your responsibility is accurate rendering and user actions, not duplicating the optimizer in the frontend.
