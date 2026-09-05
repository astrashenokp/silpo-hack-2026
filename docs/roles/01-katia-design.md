# Role 1 — Katia: Product Design in Figma

**Your main deliverable is the complete Figma design.** Give Ksiusha and Alina a draft on September 6 and the final design on September 7. You are not responsible for writing frontend code.

Read [Product](../PRODUCT.md) and [Timeline](../TIMELINE.md) first.

## Build this, in order

1. Draw the main journey: set constraints → start planner → see progress → inspect meals/products → select restocking suggestions → recalculate → preview → confirm cart addition.
2. Create the planning form: budget, days, people, optional calorie target, food preferences, restrictions, pets, recurring-purchase toggle and start button. Make units and selected states visible.
3. Design the result area: day navigation, meal cards, portions/calories, ingredient details, recipe source, recurring items, products, substitutions and totals. Keep budget remaining distinct from savings.
4. Design the connection and progress states. Users should understand what the agent has completed and what to do if sign-in/cart context is missing.
5. Design errors: invalid fields, empty history, no suitable products, unknown restriction suitability, insufficient budget, provider failure, stale preview and partial cart update.
6. Design the cart preview with existing versus added items and a separate confirmation button. Include disabled, pending, success and failure variants.
7. Create desktop and mobile layouts, reusable components and a clickable Figma prototype of the golden path. Add typography, spacing, color and component-state guidance.

Use a specialized planning page with visible controls. Do not make a message thread the primary layout. Use readable product copy; the app may be Ukrainian even though these instructions are English.

## Add these artifacts

- Figma file containing the final screens, component variants and clickable prototype.
- `docs/design/README.md`: view/prototype links, which frames are final, intended viewport sizes, navigation notes and unresolved design questions.
- `docs/design/ui-states.md`: each screen/component, its empty/loading/error/success states, button behavior and matching contract fields.
- `docs/handoffs/katia.md`: delivery notes using the [template](../templates/HANDOFF.md).
- Only the icons/images the developers need to export, with a documented location and usage permission. Do not require them to reconstruct visuals from a screenshot.

## Dates, independence and dependencies

| Date | Your output | Receiver |
|---|---|---|
| September 6 | Rough layouts, all form fields, main transitions | Ksiusha + Alina; they can begin before final styling |
| September 7 | Final Figma, component states, mobile version and handoff | Ksiusha + Alina |
| After delivery, as needed | Clarify existing design details; avoid adding scope | Frontend developers; Polina only from September 12 |

Start immediately from the product and contracts guides. You do not need MCP, Edamam, backend code or Polina. Ask Ksiusha/Alina for feasibility feedback by September 6; document open details without blocking the entire design.

## Ready-to-deliver checklist

- [ ] Both frontend developers can open the Figma links and identify final frames.
- [ ] They can follow the complete flow without asking what each button does.
- [ ] Every required product field and result section is represented.
- [ ] Mobile layout and all critical failure/confirmation states exist.
- [ ] Shared household dietary behavior, approximate calories, goods-only budget and demo labels are clear.
- [ ] A short product-story note is available for the September 14 video.

Your completion test: Ksiusha and Alina can implement their assigned screens from Figma plus your notes, without inventing missing states.
