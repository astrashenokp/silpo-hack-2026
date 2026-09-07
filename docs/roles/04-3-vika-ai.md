# Role 4.3 — Vika: Recurring purchases and budget optimization

**Deliver by September 11:** two callable modules: one that suggests recurring purchases from evidence and one that calculates/optimizes a basket against the user's constraints.

Implement both modules in Python inside the backend service. Uliana calls them directly; the Next.js frontend displays their serialized results. Keep money arithmetic in Python and preserve integer kopiykas at the JSON boundary.

Read [Product](../PRODUCT.md) and [Contracts](../CONTRACTS.md).

## Part A: recurring purchases

1. Consume Arina's normalized purchase history and its coverage information; group relevant products consistently without merging unrelated variants.
2. Implement a small reproducible rule. A reasonable starting default is at least three distinct purchase dates per product/category, then compare elapsed time to the median purchase interval. Document your actual threshold and confidence heuristic.
3. Return suggestions with interval, elapsed time, quantity/unit, confidence and a short evidence-based reason. Confidence is a heuristic score, not a statistically validated probability.
4. Handle empty/sparse history with no fabricated recurrence. Filter pet products by the explicitly selected species. Do not infer a pet's medical needs.
5. Suggestions start unselected. Prevent duplicate restocking of quantities already covered by meal requirements when the user later selects a suggestion.

## Part B: basket optimization

1. Consume Sofiia's ingredient requirements and Rina's candidate sets; reject unavailable, unsuitable or unresolved candidates.
2. Aggregate demand and calculate purchasable quantities using content size and selling increments. Check package rounding and unit conversion before costs.
3. Calculate exact line totals, basket total and budget remaining in integer kopiykas. Include selected household/pet items in money totals only.
4. Compare suitable alternatives using full required quantities, not just the lowest package sticker price. Account for verified promotional prices when available.
5. Return selected products, substitutions and their reasons, unresolved requirements and budget status. Ask Uliana for more candidates or a meal replan when needed; do not call an unbounded recursive loop yourself.
6. If no complete valid solution fits, return the shortfall. Do not quietly drop meals, shrink required servings or remove user-selected essentials to report success.
7. Report savings only from a comparable verified baseline. Otherwise return `null`; remaining budget is not savings.

## Add these files/results

- `services/api/src/smart_basket/optimization/`: recurrence logic, quantity/cost calculation and optimizer.
- `fixtures/recurring-items.json`, `fixtures/optimization-result.json` with manually verified arithmetic.
- Focused checks for sparse history, duplicate dates, package rounding, cheaper alternatives, impossible budget, restricted products and pet-cost separation.
- `docs/handoffs/vika.md`: algorithms/thresholds, units, examples, limitations and how Uliana calls both functions.

## Independence and handoffs

| Date | Your work / needed input |
|---|---|
| 5–6 | Start deterministic rules and hand-calculated examples using synthetic history/products |
| 7th | Receive Arina's history, Sofiia's ingredients and Rina's candidate fixtures; give Uliana callable signatures and optimizer output |
| 8th–9th | Validate actual prices/units and integrate with Uliana; send conversion/matching issues to Rina/Sofiia |
| 10th–11th | Exercise budget and constraint failures, merge and deliver |

No live MCP or Edamam access is needed to begin. Actual product optimization waits for Rina's live candidates; the algorithm can be complete before those arrive. Do not wait for Polina, whose work begins September 12.

## Done means

- [ ] Same inputs and evaluation date produce reproducible recurrence suggestions.
- [ ] No history means no invented pattern; pet species is respected.
- [ ] A 750 g need with 500 g packages purchases two packages and charges both.
- [ ] Basket totals match manual calculations and include only selected restocking goods.
- [ ] All required quantities/restrictions remain satisfied after replacements.
- [ ] Unavailable/unknown/over-budget cases remain explicit, with defensible explanations.
- [ ] Uliana can invoke both modules; Rina/Alina can consume the resulting selections without interpreting prose.

## Added scope: Edamam + FatSecret

With Sofiia/Rina, verify personal-portion conversion and compare available nutrition values without overwriting one provider's numbers with the other's. Deliver a hand-checked example by September 9; finish checks by September 11. A meal for three people exports one person's portion; pet food, household goods and shopping-package surplus are excluded. Rina owns provider matching and writes. Follow [the combined workflow](../FATSECRET.md).
