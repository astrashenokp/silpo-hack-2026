# Handoff: Alina — Results, progress and basket UI

- Date: September 9, 2026.
- Revision: commit `e04890b` on branch `codex/alina-planner-results` (not merged, no PR yet).
- Receivers: Rina (backend contract cross-check), Katia (design conformance), Polina (integration QA on September 12), Ksiusha (params/context screens to frame the same flow).
- Status: UI built and verified against the demo backend locally; pending merge to `main` and visual conformance against Katia's Figma.

Next.js 16 app in `apps/web`. The demo stand renders the full result flow without a backend
(fixture scenarios) and against the live demo API. The screenshot set is on Katia's Figma
(chat-desktop layout); mobile mocks are not available yet, so the layout is already
adaptive but has not been reviewed against any phone mock.

## What is built

- `src/lib/api/types.ts` — TypeScript mirrors of `packages/contracts/openapi.json` (camelCase, kopecks-as-integers).
- `src/lib/api/client.ts` — fetch client behind the local rewrite `/api/:path*` → `http://127.0.0.1:8000/api/:path*`: `/plans`, `/plans/{runId}`, recalculate, `/cart/preview|confirm`, `/integrations/fatsecret`, `/fatsecret/exports/preview|confirm|get`, polling, `X-Demo-Scenario` header, `crypto.randomUUID()` idempotency keys.
- `src/lib/api/fixtures.ts` — the shared `fixtures/*.json` imported as demo payloads plus derived in-memory scenarios (over-budget, incomplete matching, empty history, recurring suggestions, running progress).
- `src/lib/format.ts` — kopecks→UAH, quantities, servings, slot labels, restriction/budget labels, stage texts (`Профіль та меню зчитано…`, `Історія покупок зчитана…`, `Меню сформовано…`, `Підбір продуктів Сільпо…`, `Оптимізація цін та кошику Сільпо…`, `Готово`).
- `src/features/planner-results/` — `PlannerResults` orchestrator plus components: `RunProgress`, `states` (EmptyHistoryBanner, AgentFailure, SyncFailureModal, WarningsList), `MealPlan` (+ FatSecret meal toggle), `RecurringSuggestions`, `ProposedBasket`, `BudgetSummary`, `CartPanel`, `CartFlow` (preview modal, per-item receipt), `FatSecretFlow` (preview modal, export outcome).
- `src/app/page.tsx` — demo hub: fixture scenario chips and a live-backend panel with scenario selector.

## Verification

- `npm run lint` and `npm run build` pass in `apps/web`.
- Live flow verified through the rewrite against the demo backend (`services/api` on `127.0.0.1:8000`): context, create plan → poll → completed, recalculate (version bump), cart preview/confirm for success/partial/failed, idempotent retry with the same key, FatSecret status/preview/confirm/export including `unmatched` (blocks confirm).

Ways to drive the app:

```bash
services/api/.venv/bin/python -m uvicorn smart_basket.app:app --host 127.0.0.1 --port 8000 --app-dir services/api/src
cd apps/web && npm run dev   # http://localhost:3000
```

The live panel starts with GET `/api/context`; "Скласти меню та кошик" posts
`fixtures/planning-request.json` and polls. The demo-scenario header is only sent on
preview calls — the backend stores the scenario at preview time and replays it on
confirm, so confirm/retry never changes the outcome or double-adds.

## Decisions and notes

- Fixture JSONs are copied into `apps/web/src/fixtures/` because Turbopack (Next 16 build
  default) blocks module resolution outside the web app root. Keep them in sync with the
  shared `fixtures/` when the backend updates payloads.
- The screen follows the chat-desktop mock. This contradicts the earlier PRODUCT.md line
  "do not make a message thread the primary layout"; Katia's mocks take precedence.
- Every demo payload is visibly badged (`ДЕМО / СИНТЕТИКА`, `ЖИВІ ДАНІ`, `ЗМІШАНІ ДЖЕРЕЛА`) and
  per-product source (`Сільпо`/`Демо`); a synthetic basket is never presented as a
  server-confirmed cart. The receipts show the exact provider message back.
- Cart confirm is a two-stage gate: "Додати все в кошик Сільпо" opens a preview modal
  (existing vs. added quantities + totals + expiry), "Підтвердити додавання" sends
  confirm with an idempotency key. A failed/syncing receipt keeps the preview and key so
  "Повторити синхронізацію" re-sends the same operation; "Спробувати пізніше" closes it.

## Open questions (mostly for Katia; none block v0.1)

- `−/+` editing of a live cart item: out of v0.1 scope per contract (the panel note says
  quantity in the real cart is managed in Silpo).
- Who supplies `savingsMinor` (discount/`Реальна економія`); the UI shows `—` when null.
- "Перейти до оплати Сільпо" is intentionally not implemented; MVP ends at cart checkout.
- Defaults for `RecurringSuggestion.selected` come from the contract; toggling any item
  marks the basket "потрібне перерахування" and disables the old confirmation until recalc.

## Next steps (me, or whoever picks this up)

- Open a PR from `codex/alina-planner-results` and resolve any merge conflicts with Ksiusha's input screen.
- Validate the grid/day tabs, cart panel and error modals against Katia's final Figma; I could
  not read the images directly, so Alina described them in text.
- Connect the demo hub's live panel to Ksiusha's real parameters screen when it lands.