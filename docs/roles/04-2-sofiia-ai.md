# Role 4.2 — Sofiia: Edamam, meals and ingredients

**Deliver by September 11:** a meal-planning module that returns recipes/meals, servings, calorie estimates and normalized ingredient requirements for product matching.

Write this as a Python module in the shared backend. Uliana calls it through Python; meal data reaches the Next.js UI through Rina's JSON API. Keep Edamam credentials and provider requests in Python.

Read [Product](../PRODUCT.md), [Contracts](../CONTRACTS.md) and [Edamam notes](../INTEGRATIONS.md#edamam--sofiia-owns-the-adapter).

## Implement in this order

1. By September 6, verify the actual Meal Planner account/credentials, request shape, limits and access to recipe/ingredient fields. Record the result and blockers for Uliana.
2. Define supported preference/restriction label mappings. Give Ksiusha the list by September 7. Reject unsupported hard restrictions explicitly rather than pretending a provider filter exists.
3. Implement `build_meal_plan(request, effectiveContext)` using Edamam as the primary source. Cover every requested day and breakfast/lunch/dinner for the shared household diet.
4. Normalize recipes and servings. Scale ingredient needs by requested people divided by original recipe servings; avoid scaling twice if the provider already supplies adjusted quantities.
5. Aggregate equivalent ingredient requirements across meals. Normalize reliable measurements to grams, milliliters or pieces and preserve meal references. Unconvertible quantities remain unresolved; never guess a cup's mass without a valid ingredient-specific conversion.
6. Pass source links, attribution and available per-serving calorie estimates to the result. Translate/normalize ingredient search terms for Silpo matching with Rina.
7. Support Uliana's bounded replan request after Vika reports budget pressure. Preserve portions/restrictions; use cheaper ingredient choices where possible without promising prices before catalog matching.
8. Add explicit timeout/rate-limit/error behavior and an opt-in synthetic fixture fallback for development/demo. Do not store provider recipe payloads as repository fixtures.

## Add these files/results

- `services/api/src/smart_basket/meals/`: Edamam adapter, request/filter mapping, serving scaling and ingredient normalization.
- `fixtures/meal-plan.json`, `fixtures/ingredients.json`: original synthetic meals with consistent servings/quantities and clear source labels.
- Edamam setting names and access instructions for Rina's configuration handoff.
- `docs/handoffs/sofiia.md`: verified fields, filter mapping, units/scaling assumptions, attribution requirements, errors, limits and live/mock checks.

## Inputs, outputs and dates

| Date | Dependency / handoff |
|---|---|
| 6th | Verify Edamam access independently; report feasibility to Uliana |
| 7th | Give module signature and meal/ingredient fixtures to Uliana, Rina and Vika; UI labels to Ksiusha and attribution shape to Alina |
| 8th–9th | Connect live meal planning with Uliana and resolve ingredient/product unit issues with Rina/Vika |
| 10th–11th | Check restrictions, calories, scaling, missing measurements and failure paths; deliver final module |

Start adapter design, scaling and synthetic fixtures without backend/AI completion. Live Edamam verification requires credentials. Product matching and final price optimization require Rina/Vika later, but they do not block your meal module. Polina first receives your handoff September 12.

## Done means

- [ ] Requested days and meal slots are covered, or incompleteness is explicitly reported.
- [ ] Servings and ingredient quantities are internally consistent and manually checked for a 3-person example.
- [ ] Hard restrictions survive initial planning and replanning; unsupported filters are reported.
- [ ] Unknown calories/measurements are not fabricated.
- [ ] Ingredient IDs and meal references allow Rina to match and Alina to display requirements.
- [ ] Live output provides source/attribution information and respects the account's actual available fields.
- [ ] Uliana can call the module with mocks and the real provider using the same interface.

You own meals and ingredient demand. Rina finds purchasable products; Vika computes their cost and budget fit.

## Added scope: Edamam + FatSecret

Keep Edamam as the meal-planning source. Add `Meal.ingredientAmounts` alongside the aggregate shopping list: quantities for that specific meal's `servings`, with reliable units and preparation basis. Give Rina/Vika an example and schema by September 8 so they can calculate one personal portion correctly; finish by September 11. Document which Edamam-derived fields the actual plan permits exporting/persisting before enabling the live export, and preserve required attribution. Use original synthetic recipes for fixtures. Follow [the combined workflow and v0.2 contract](../FATSECRET.md).
