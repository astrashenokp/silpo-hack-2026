# Handoff: Alina — Results, progress and basket UI

- Date: September 10, 2026.
- Revision: `codex/alina-planner-results` (not merged, no PR yet).
- Receivers: Rina (backend contract cross-check), Katia (design conformance), Polina (integration QA on September 12), Ksiusha (params/context screens to frame the same flow).

Next.js 16 app in `apps/web`. The demo stand renders the full result flow without a
backend (fixture scenarios) and against the live demo API. The layout follows the
chat-desktop mock; mobile layout is adaptive but not yet reviewed against a phone mock.

## Current UX (v0.2)

- **Chat hub** (`src/app/page.tsx`): multiple independent chats (create/delete), a single
  **shared cart** across all chats (page-level state passed to every `PlannerResults`), a
  shared **saved-meals list**, and a bottom chat bar whose sent messages render as user
  bubbles at the very bottom of the thread (autoscroll on send).
- Demo scenario switcher UI was removed from the sidebar by design; demo states are still
  reachable programmatically via `selectDemo(key)` / `buildDemo(key)`.
- **Restocking**: products that are linked to `recurringItems` (via `recurringSuggestionIds`)
  get *include/exclude* toggles on the same product cards; toggling marks the basket
  «потрібне перерахування», disables «Додати все в кошик Сільпо» and «Синхронізувати з
  Сільпо» until «Перерахувати кошик» completes. The default demo fixture has no restocking
  items, so its visuals are unchanged.
- **Budget states**: ready view shows explicit warnings for over-budget (`budgetRemainingMinor < 0`)
  and incomplete (`budgetStatus === "incomplete"`) and gates the add-all button with the same
  `canConfirmCart` rule the cart panel uses.
- **Empty history**: `EmptyHistoryBanner` renders when the result carries a history warning.
- **FatSecret (hybrid)**: heart toggle on meal cards keeps meals in a shared saved list; the
  «Збережені у FatSecret» tab lists them and offers **«Зберегти у FatSecret»**, which opens a
  preview (`FatSecretPreviewModal`: destination account, Saved Meals, one personal portion per
  meal, kcal comparison) and then a per-meal outcome view (success/partial/failed + read-back).
  Synthetic and clearly labelled; repeated export reuses the same operation (no duplicates).

## What is built

- `src/lib/api/types.ts`, `client.ts`, `fixtures.ts`, `format.ts` — as in v0.1.
- `src/features/planner-results/` — `PlannerResults` orchestrator (shared cart via controlled
  props) plus live components: `RunProgress`, `states` (EmptyHistoryBanner, AgentFailure,
  SyncFailureModal, WarningsList), `CartPanel`, `CartFlow`, `FatSecretFlow` (preview + outcome).
- `src/app/page.tsx` — chat hub described above.
- Un-wired reference components from v0.1 remain in the tree and compile but are not rendered
  by the current chat design: `MealPlan`, `ProposedBasket`, `RecurringSuggestions`,
  `BudgetSummary`.

## Verification

- `npm run lint` and `npm run build` pass in `apps/web`.
- Live flow verified against the demo backend (`services/api` on `127.0.0.1:8000`): context,
  create plan → poll → completed, recalculate (version bump), cart preview/confirm for
  success/partial/failed, idempotent retry with the same key.
- Manual demo checks: chat create/delete, cart persists across chat/tab switches, FatSecret
  preview/confirm/outcome, budget and empty-history states via `selectDemo`.

```bash
services/api/.venv/bin/python -m uvicorn smart_basket.app:app --host 127.0.0.1 --port 8000 --app-dir services/api/src
cd apps/web && npm run dev   # http://localhost:3000
```

## Decisions and notes

- Design rework keeps the chat-desktop mock (Katia's mocks take precedence over the earlier
  PRODUCT.md "no message thread" line).
- The cart is a single shared cart owned by the page; naming of the store/cart header comes
  from the active chat's result while positions/quantities are shared.
- Every demo payload is visibly badged (`ДЕМО / СИНТЕТИКА`, `ЖИВІ ДАНІ`, `ЗМІШАНІ ДЖЕРЕЛА`);
  a synthetic basket or export is never presented as a server-confirmed one.
- Cart confirm is a two-stage gate (preview → confirm with idempotency key); FatSecret export
  reuses the same operation on repeat clicks.

## Open questions

- `−/+` editing of a live cart item is out of v0.1 scope per contract.
- Who supplies real `savingsMinor`; the UI shows `—` when null.
- Real FatSecret end-to-end saving still needs Arina/Rina live account path; demo is synthetic.
- "Перейти до оплати Сільпо" is intentionally not implemented; MVP ends at cart checkout.

## Next steps (me, or whoever picks this up)

- Open a PR from `codex/alina-planner-results` and resolve conflicts with Ksiusha's screens.
- Validate against Katia's final Figma (including phone layouts).
- Record the golden demo input (3 people, 4 days, UAH 1,800, ~2,000 kcal, vegetarian, 1 cat,
  history analysis on) for Polina's September 12 intake.