# What we are building

## User outcome

“I set my household's needs and budget, receive a meal plan and matching Silpo products, review the proposal, then add the approved products to my Silpo cart.”

The user can also save selected meals from the Edamam-based plan into their connected FatSecret account. The initial scope is reusable Saved Meals for one person's portion, not dated diary entries. Follow [the combined workflow](FATSECRET.md) for implementation and account/app verification.

Build a standalone demonstration web page that could later fit into the Silpo website. Access to publishing inside the official Silpo website is not assumed.

## Page sections and controls

| Section | What the user sees or does | Implementation owner |
|---|---|---|
| Silpo context | Connect account; see connection status and active store/cart context | Ksiusha + Arina |
| Budget | Enter UAH; label explains that this covers all selected goods for the period | Ksiusha |
| Period and people | Choose days, household size and optional kcal target per person per day | Ksiusha |
| Food preferences | Select visible chips/buttons; restrictions and allergens have a separate control | Ksiusha |
| Pets | Toggle pet needs, choose species and count | Ksiusha |
| Recurring purchases | Toggle whether to analyze purchase history for restocking suggestions | Ksiusha |
| Start | “Create plan”; inline validation; prevent accidental duplicate launches | Ksiusha |
| Progress | Completed actions and the current stage | Alina |
| Meal plan | Days, meals, portions, estimated calories, ingredients, recipe source | Alina |
| Restocking | Suggested items, short explanation, include/exclude controls | Alina |
| Proposed basket | Products, packages, quantities, prices, substitutions, total and budget difference | Alina |
| Recalculation | “Recalculate basket” after changing selected restocking items | Alina + Rina + Vika |
| Real cart | “Add to Silpo cart” → preview changes → “Confirm addition” → verified outcome | Alina + Rina |
| FatSecret connection | “Connect FatSecret”; connection status and destination account | Ksiusha + Arina |
| Save meals | Select meals → “Save to FatSecret” → preview personal portions → “Confirm saving” → per-meal outcome | Alina + Rina; Sofiia supplies meal quantities |

Katia designs every section and state in Figma, including desktop and narrow mobile layouts. Optional “Additional wishes” text must not silently override structured restrictions. Product-facing interface copy can be Ukrainian; repository instructions are English.

## Required MVP by September 11

- One complete journey: form → context/history → meals → ingredients → products → optimization → review → confirmed cart addition.
- Budget, days, people, calorie target, preferences, restrictions and pet inputs.
- Real official Silpo MCP use for context/history, product data and cart operations.
- Edamam as the primary external meal-planning service; clearly labeled synthetic fixtures for independent development and a backup demonstration.
- FatSecret account connection and saving selected meals using the [specified export flow](FATSECRET.md). Verify live app visibility and supported data use; explicitly report an incomplete integration if blocked. FatSecret failure must not prevent planning or Silpo cart use.
- Basic recurring-purchase analysis and pet restocking based on the explicitly selected species.
- Full-package cost calculations and a simple search for suitable cheaper alternatives.
- Loading, empty, missing-data, integration-error, insufficient-budget and partial-cart-update states.

## Deferred features

Free-form chat, voice, calendar, party workflows, a separate diet for every family member, advanced prediction, medical advice, loyalty optimization, payment and order placement. A full delivery/address selection UI is also deferred. Use an existing valid cart context; if missing, explain that the user must configure it in Silpo and reconnect. Reading and validating the context is still required for the MVP.

FatSecret automatic diary entries, date-based weekly-plan synchronization and continuous two-way updates are also deferred. Saving a reusable meal is the initial export behavior.

## Shared product decisions

1. MVP uses one shared set of dietary restrictions for the household. If one person is vegetarian, offer a shared vegetarian menu and make that assumption visible. Individual menus are future work.
2. Restrictions take priority over cost. Unknown ingredient/allergen information must not be treated as verified suitability. Unresolved required products block cart confirmation.
3. Merge saved and explicit restrictions; surface conflicts. Confirmed form values control budget, period, people and preferences.
4. Calories are estimates. Display targets and available estimates separately; do not invent missing nutrition. Pet food and household items do not contribute to human meal calories.
5. The budget covers meal products plus selected recurring/pet items. Delivery is excluded and labeled separately. Do not claim the goods total is the checkout total.
6. If the budget is unrealistic, show the shortfall or incomplete result. Do not silently reduce people, necessary portions or restrictions.
7. Restocking suggestions require selection. Selecting/removing them recalculates the proposal before cart confirmation.
8. Planning does not mutate the real cart. Only confirmation of a concrete current proposal permits cart changes. No payment or order placement.
9. Show short action summaries, not private model reasoning. Clearly label synthetic data and any fallback source.
10. Saving to FatSecret and adding to Silpo are independent, explicitly confirmed actions. FatSecret receives the reviewed personal meal quantities, not the household shopping list, package sizes or pet/household goods.

## Golden demo input

3 people, 4 days, UAH 1,800, about 2,000 kcal per person per day, shared vegetarian meals, 1 cat, recurring-purchase analysis enabled. This is a test input, not a promise that live prices make the full request feasible at that budget.

Demonstrate structured input, retrieved context, meals, justified restocking when history supports it, ingredient-to-product matching, cost calculation, optimization and confirmed cart addition. If live prices exceed the budget, demonstrate that state honestly and adjust the input through the UI.
