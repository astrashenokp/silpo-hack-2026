# Bug list

Final-integration defects found by Polina. Each author fixes her own module
([decision owners](../WORKFLOW.md#decision-owners)); Polina retests and updates the
status here. Results of each run are in [test results](test-results.md).

Severity: **Blocker** stops setup or the demo flow; **High** breaks a required
feature; **Medium** misleads the user or a reviewer; **Low** is cosmetic or
documentation.

Found on `main` @ `0ef7fbb` (September 11, 2026); the latest retest is run 5 on `afe586e`
(`main` with #26 plus PR #27). This list has not yet been sent to the owners; Polina shares it
with the team.

| ID | Severity | Summary | Owner | Status |
|---|---|---|---|---|
| BUG-001 | Blocker | Backend cannot be installed or tested from a clean checkout (`pyproject.toml` syntax error) | Rina (file owner); introduced by merge `f7b10e0` from Uliana's branch | Fixed in #20; retested ✅ (run 4) |
| BUG-002 | Blocker | Web UI never calls the Python API: plan, cart and FatSecret are simulated in the browser | Ksiusha + Alina | Fixed in #27 (Polina); retested ✅ (run 5) |
| BUG-003 | High | "Recalculate basket" always fails with `PLANNER_FAILED` and leaves no confirmable plan | Uliana | Fixed in #22; retested ✅ (run 4) |
| BUG-004 | High | Chat tests abort the backend suite without `GEMINI_API_KEY`; with a key 3 of 10 still fail | Uliana | Fixed in `5fcd4b4` (Sofiia); retested ✅ (run 5) |
| BUG-005 | High | Unsupported dietary restrictions typed in the form are silently moved into `notes` | Ksiusha | Fixed in #31 (Polina); retested ✅ (run 5) |
| BUG-006 | Medium | Invented, unlabeled cart panel, store address and user name in the UI | Alina + Ksiusha | Fixed in #31 (Polina); retested ✅ (run 5) |
| BUG-007 | Low | Days counter stops at 7; the contract allows 1–14 | Ksiusha (confirm with Katia) | Open |
| BUG-008 | Low | `API_BASE_URL` is documented as runtime configuration but only applies at `next build` | Ksiusha | Open |
| BUG-009 | Medium | Text contrast below WCAG AA on primary buttons, hints and the cart panel | Katia + Ksiusha + Alina | Open |
| BUG-010 | Low | OpenAPI omits the allowed `X-Demo-Scenario` values; 405 responses lack `Allow`; three operations also accept schema-valid bodies the API rejects on uniqueness/label rules the schema does not express | Rina | Open; extended in run 7 |
| BUG-011 | High | Invented regular purchases (whiskey, butter), prices and brand images are shown as plan data | Alina + Ksiusha | Fixed in #31 (Polina); retested ✅ (run 5) |
| BUG-012 | High | Cart: "Додати все" skips the preview, and the preview is always stale, so it cannot be confirmed | Alina | Fixed in #27 and #31 (Polina); retested ✅ (run 5) |
| BUG-013 | Medium | Public-deployment hardening: unbounded sessions and runs, no rate limit, cookie without `Secure` | Rina | Open |
| BUG-014 | Medium | The generated OpenAPI contract is stale after the live cart changes (`export_contracts.py --check` fails) | Rina | Fixed in `5fcd4b4` (Sofiia); retested ✅ (run 5) |
| BUG-015 | High | Since the shared cart (`1a121e0`), windows narrower than 1280 px have no cart panel, so the cart cannot be synced or confirmed | Alina | Fixed in #31 (Polina); retested ✅ (run 5) |
| BUG-016 | Medium | An over-budget plan can be added and synced to the cart, while the contract says to disable confirmation | Alina; decision with Rina and Katia | Fixed in #31 (Polina); retested ✅ (run 5) |
| BUG-017 | Medium | `GET /api/fatsecret/exports/confirm` and `.../preview` are swallowed by the parameterized `GET /api/fatsecret/exports/{export_id}` route and answer 404 instead of 405 | Rina | Found in run 7 (Schemathesis) |
| BUG-018 | Low | The per-day calorie figure was labeled "average per day" but was an average across that day's meals (e.g. shows ~620 next to a 2000 kcal/day target, reading as a huge shortfall that isn't real) | Polina (own file, `apps/web/src/features/planner-results/components/MealPlan.tsx`) | Fixed on `feature/polina-qa-run13`; retested ✅ (run 13, e2e 40/40, UI 24/24) |
| BUG-019 | Low | The hosted API has no real `GEMINI_API_KEY`, so chat on the live deploy always answers "Чат недоступний: ... GEMINI_API_KEY" instead of doing anything — this is the documented fallback behavior working correctly, not a crash, but chat cannot be demoed live without a real key | Uliana (owns the chat module and any Gemini key); Polina to add it as a Northflank runtime variable once supplied | Open — blocked on a real key |

## BUG-001 — Backend cannot be installed or tested from a clean checkout

- **Where:** `services/api/pyproject.toml:11` reads `<dependencies = [`. The stray `<`
  arrived with merge commit `f7b10e0` ("Merge branch 'main' into uliana/ai-chat-agent").
- **Steps:** from the repository root run `python -m venv services/api/.venv`, then
  `& services/api/.venv/Scripts/python.exe -m pip install -e 'services/api[test]'`.
- **Actual:** `ERROR: ...services\api\pyproject.toml: Invalid statement (at line 11, column 1)`.
  `pytest services/api/tests` aborts with the same message because pytest reads that file
  as its configuration.
- **Expected:** the install and test commands in `services/api/README.md` work.
- **Impact:** blocks clean setup, CI, the API Docker image and deployment. Intake continued
  with a local workaround only: dependencies installed by name, `PYTHONPATH=services/api/src`,
  a neutral pytest configuration.
- **Fix hint:** delete the `<`.

## BUG-002 — Web UI never calls the Python API

- **Where:**
  - `apps/web/src/app/page.tsx:277` always renders `<PlannerForm demoMode …>`; every chat is
    created with `mode: "fixtures"` (lines 108, 157, 173) and nothing switches it to `live`.
  - `apps/web/src/features/planner-input/PlannerForm.tsx:171-186` fakes the context;
    `:458-496` returns `fixturePlanningResult`, replacing only the budget fields and
    `effectiveRequest`.
  - `apps/web/src/features/planner-results/PlannerResults.tsx:193,212` use
    `fixtureCartPreview` and `fixtureCartPartial` while `sourceMode === "fixtures"`.
  - `page.tsx:217-230` builds the FatSecret preview and export in the browser; the Silpo and
    FatSecret connect buttons (`page.tsx:437-444`, `:464`) only change local state.
- **Steps:** open the app, continue as guest or "connect", start planning, choose 1 person and
  2 days, enter a budget and create the plan.
- **Actual (code inspection of `0ef7fbb`; no browser click-through was recorded):** no request
  reaches `POST /api/plans`. The result is always the 4-day, 3-person fixture menu while
  `effectiveRequest` shows the form values. Cart confirmation shows the fixture partial
  receipt. FatSecret saving never calls the API, and "connected" is simulated.
- **Expected:** form → `POST /api/plans` → poll → render; cart through `/api/cart/*`;
  FatSecret through `/api/integrations/fatsecret` and `/api/fatsecret/exports/*`; the connect
  buttons navigate to `/api/auth/silpo/start` and `/api/auth/fatsecret/start`. A fixture view
  may remain as an explicitly chosen, labeled mode.
- **Impact:** a hosted demo would show neither the Python pipeline nor any MCP or FatSecret
  call, so "full demo uses verified real MCP calls" cannot be met. The API side works through
  Next.js forwarding (end-to-end suite through `:3000`: 34 passed, 1 known failure).
- **Fix (#27, Polina; retested in run 5):** new chats run against the API. The form posts to
  `/api/plans` and polls the run; "↻ Перерахувати кошик" calls `/api/plans/{runId}/recalculate`;
  the cart preview and confirmation go through `/api/cart/*`; FatSecret through
  `/api/fatsecret/exports/*`; the connect buttons open `/api/auth/silpo/start` and
  `/api/auth/fatsecret/start`, and the statuses are read after the return. The result shows the
  API's `dataMode`. `tests/ui/specs/api-wiring.spec.ts` passes as a regular check. Still in the
  browser only: the chat, which has no API endpoint, and the invented data of BUG-006 and BUG-011.

## BUG-003 — "Recalculate basket" always fails

- **Where:** `services/api/src/smart_basket/agent/orchestrator.py:939-942` builds
  `MatchingContext(session=..., emit_progress=...)`. `MatchingContext`
  (`catalog/matching.py:18-21`) takes `session`, `catalog` and `check_restrictions`, so the
  worker raises `TypeError`, which the API reports as `PLANNER_FAILED`.
- **Steps:** `GET /api/context`; `POST /api/plans` with `fixtures/planning-request.json` →
  completed; `POST /api/plans/{runId}/recalculate` with
  `{"version": 1, "selectedRecurringIds": []}` → 202; poll the new run.
- **Actual:** the new run ends `failed` with
  `{"code": "PLANNER_FAILED", "message": "Planner could not produce a valid result.", "retryable": true}`.
  The original run is already superseded (`routes/api.py:192`), so `POST /api/cart/preview`
  for it returns 409 `STALE_PLAN`: the user has no confirmable plan left and must start over.
- **Expected:** a completed run with `version: 2` and the unchanged `effectiveRequest`.
- **Also failing:** `services/api/tests/test_api.py::test_stale_cart_previews_block_changes[recalculate]`
  (line 191); end-to-end `test_recalculation_returns_next_version` (marked `xfail`).
- **Note for Rina:** consider superseding the original run only after the recalculated result
  is ready, so a failed recalculation does not strand the user.

## BUG-004 — Chat tests break the backend suite

- **Where:** `services/api/tests/test_uliana_chat_flow.py`.
- **Actual:** without `GEMINI_API_KEY`, collecting the module raises
  `RuntimeError: GEMINI_API_KEY is not configured.` and pytest stops before any test runs.
  With a dummy key: 5 passed, 5 failed —
  `MatchingContext.__init__() got an unexpected keyword argument 'emit_progress'` (2 tests,
  same root cause as BUG-003), `assert 49000 == 34000` (2 tests; expected totals predate the
  current meal module), and the explanation test expects `1460.00 UAH` while the plan reports
  `1310.00 UAH`.
- **Retest (run 4, after #22):** the `MatchingContext` failures are gone. Collection without a key
  still fails, and with a dummy key 3 tests still fail on the stale expectations (`34000` twice,
  `1460.00 UAH`).
- **Expected:** the suite runs and passes without secrets, with Gemini mocked or injected.
- **Impact:** CI stays red and the handoffs' test counts cannot be reproduced.
- **Retest (run 5, `afe586e`):** fixed. No test module reads `GEMINI_API_KEY` any more
  (`5fcd4b4`, Sofiia), and the documented command passes all 191 tests without it, Uliana's new
  chat tests from #26 included.

## BUG-005 — Unsupported restrictions are silently moved into notes

- **Where:** `apps/web/src/features/planner-input/PlannerForm.tsx:313-341` maps only
  `peanut-free` ("без арахісу", "арахіс") and variants of "vegetarian"; `:393-421` puts every
  other entry into `notes`.
- **Actual:** "gluten-free", "без глютену", "vegan", "горіхи" and similar entries are sent as
  free text in `notes` with `restrictions: []`.
- **Expected:** offer the labels from `GET /api/filters` (5 preferences, 8 restrictions, listed
  in Sofiia's handoff) and reject or explain anything else. Contract: "Reject unsupported
  restriction labels with an explanation rather than ignoring them"; product rule: notes must
  not silently override structured restrictions.
- **Impact:** an allergen the user entered is not enforced although the UI accepted it.
  Live since #27: the form now sends these requests to the API.

- **Retest (run 5, since #31):** fixed. The form's "Алергени та заборони" and "Вподобання"
  fields now load their choices from `GET /api/filters` and let the user pick only from that list;
  everything typed reaches `PlanningRequest.restrictions`/`.preferences` instead of free text in
  `notes`. Confirmed by `tests/ui/specs/a11y.spec.ts` and the UI walk-through in run 5.

## BUG-006 — Invented, unlabeled data in the UI

- **Retest (run 5, since #31):** fixed. The result screen now renders the API's own meal
  plan, product list and recurring suggestions instead of the fixed cards; the greeting no
  longer names anyone, and the cart panel shows the store label only when the API supplies
  one, with a demo note otherwise. Confirmed by `tests/ui/specs/flows.spec.ts`.

- **Where:** `apps/web/src/app/page.tsx:532-585` (`SetupCartPreview`: two
  "Масло солодковершкове Галичина" items at 124.00/79.99 ₴, a discount total and the store
  "просп. Бандери, 23 (Самовивіз)"); `page.tsx:405` and `:662` greet "Катерина"/"Катерино"
  after the simulated connection. `apps/web/src/features/planner-results/PlannerResults.tsx:380`
  greets every user, guests included, with "Привіт, Катерино!", and `:258` and `:361` show a
  fixed "10:39" time. Confirmed at runtime in run 3 (`tests/ui/specs/flows.spec.ts`).
- **Expected:** synthetic data is visibly labeled (product decision 9); no invented store,
  cart contents or person.
- **Impact:** viewers of the video can take the panel for the user's real Silpo cart.

## BUG-007 — Days counter stops at 7

- **Where:** `apps/web/src/features/planner-input/PlannerForm.tsx:981,988` (`max={7}`).
- **Expected:** 1–14 as in `docs/CONTRACTS.md` and the backend validation, or a deliberate
  design limit recorded by Katia.

## BUG-008 — `API_BASE_URL` only applies at build time

- **Where:** `apps/web/next.config.ts` rewrites. `docs/handoffs/ksiusha.md` and
  `services/api/README.md` describe `API_BASE_URL` as a setting of the running frontend.
- **Evidence:** after a build with the default, `API_BASE_URL=http://127.0.0.1:8999 npx next start -p 3001`
  still answers `/api/health` from the API on `:8000`; `.next/routes-manifest.json` contains
  the literal destination.
- **Impact:** a different API address needs a rebuild. `deploy/web.Dockerfile` passes it as a
  build argument; the frontend handoff should say so.

## BUG-009 — Text contrast below WCAG AA

- **Found in:** run 2, axe-core 4.13.0 `color-contrast` rule (WCAG 2.1 AA 1.4.3) through
  `tests/ui/specs/a11y.spec.ts` (PR #19). Account gate: 5 elements; planner form: 16 on
  desktop, 5 on mobile.
- **Actual (text on background, measured ratio):** white on the brand orange `#F89F46`
  2.09:1 on every primary button ("Новий чат", "Підключити акаунт Сільпо",
  "Скласти меню та кошик") and the "-35%" badges; `#8E8E93` "Чати" label 3.26:1;
  `#8B7357` on `#F5E6D2` guest button 3.65:1; hints and unit suffixes in `text-black/50`
  3.94:1; `#9AA1AD` timestamp 2.6:1; `#7D8798` store line 3.62:1; cart panel `#9A9A9A`
  2.81:1, `#22A06B` discount 3.32:1, `#777777` old price 4.47:1.
- **Expected:** at least 4.5:1 for normal text (3:1 for text of 24 px, or 18.66 px bold, and
  larger), for example dark text on the orange or a darker orange behind white text.
- **Impact:** hard to read for low-vision users and in a recorded video; Lighthouse
  accessibility is 95 instead of 100. The spec annotates this rule as a known issue until it
  is fixed.

## BUG-010 — Contract details found by Schemathesis

- **Found in:** run 2, Schemathesis 4.26.1 via `tests/contract/run_schemathesis.py` (PR #19).
- **Actual:**
  - `packages/contracts/openapi.json` declares `X-Demo-Scenario` as free text, while the API
    accepts only listed values (`success`/`failed` for plans, plus `partial` for cart previews
    and `unmatched` for FatSecret previews) and answers 400 otherwise, including for an empty
    header. Three schema-valid requests were rejected this way.
  - 405 responses (for example `TRACE /api/plans`) have no `Allow` header, which RFC 9110
    requires: the generic `HTTPException` handler in `services/api/src/smart_basket/app.py:76-80`
    rebuilds the response without the original headers. 13 operations are affected.
- **Expected:** the header values as an enum in the OpenAPI contract, and 405 responses that
  keep `Allow`.
- **Extended in run 7 (`main` @ `100343e`, Schemathesis 4.26.1, 50 examples per operation,
  `--continue-on-failure`, 1360 cases generated, 5 unique failures reproduced consistently across
  two runs; JUnit report `tests/contract/reports/junit-20260912T155003Z.xml`):**
  - `POST /api/plans` accepts `restrictions: [""]` per the schema (`list[str]`), but the API
    rejects it with `VALIDATION_ERROR: Unsupported restrictions: `. The label set is a fixed
    enum in `schemas/__init__.py:44-50`, not expressed in the generated contract.
  - `POST /api/plans/{runId}/recalculate` accepts duplicate or empty `selectedRecurringIds` per
    the schema, but the API requires unique, known IDs (`routes/api.py:207-208`) and answers 400.
  - `POST /api/fatsecret/exports/preview` accepts duplicate `mealIds` per the schema, but the API
    requires unique IDs from the plan (`fatsecret/export.py:84`) and answers 400.
  - Two of the "unsupported method" failures this run are BUG-017, not a contract gap:
    `GET /api/fatsecret/exports/confirm` and `.../preview` should answer 405 and instead reach
    `GET .../{export_id}`. The other four operations Schemathesis flagged as "repeatedly 404"
    (`POST /api/cart/preview`, `POST /api/cart/confirm`, `POST /api/fatsecret/exports/confirm`,
    `GET /api/fatsecret/exports/{export_id}`) are not a defect: a fuzzer without a real
    `runId`/`previewId` in this session can only ever reach the "not found" branch of those
    routes.

## BUG-011 — Invented regular purchases, prices and brand images shown as plan data

- **Retest (run 5, since #31):** fixed. `RecurringSuggestions`, `MealPlan` and
  `ProposedBasket` render only `result.recurringItems`, `result.mealPlan` and
  `result.selectedProducts`; the fixed butter and whiskey cards, their images and
  `apps/web/public/butter-galychyna.png` are deleted. Selecting a recurring item is disabled
  with a stated reason, because the API cannot match one to a product yet (CR-04); the
  suggestion itself is real, not invented.

- **Found in:** run 3 UI walk-through (desktop and Pixel 7); confirmed by
  `tests/ui/specs/flows.spec.ts` (`test.fail`).
- **Where:** `apps/web/src/features/planner-results/PlannerResults.tsx:684`, `:702` and `:714`
  define fixed "Регулярні покупки" items ("Масло солодковершкове Галичина" and "Віскі Jameson",
  each shown twice); `:954`, `:1002` and `:1019-1020` attach butter or whiskey names, prices and
  images to meal ingredients. `apps/web/src/components/ui/ProductImage.tsx:9-16` hotlinks the
  Jameson image from `ik.imagekit.io/.../jamesonwhiskey/...` and the oats, rice and lentil photos
  from Wikimedia Commons; `apps/web/public/butter-galychyna.png` is a brand product photo.
- **Actual:** a guest without purchase history sees "Регулярні покупки" with two butter packs
  (79.99 ₴) and two bottles of whiskey (629.00 ₴). Ingredient rows carry the same prices, for
  example "Dry oats 150 g — 124.00 → 79.99 ₴" with the butter photo and
  "Dry lentils 90 g — 899.00 → 629.00 ₴" with the whiskey photo, while the budget summary below
  says 490 грн.
- **Expected:** recurring suggestions only from `result.recurringItems` (empty for a guest; the
  contract forbids invented recurrence); ingredient rows with quantities from `ingredientAmounts`
  and prices only from `selectedProducts`; no alcohol unless it comes from the user's own history;
  images with known rights, or none.
- **Impact:** looks like fabricated results in the video (grounds for disqualification under the
  rules), recommends alcohol in a Silpo-branded family planner, and uses third-party brand images
  without recorded rights ([submission checklist](submission.md)).

## BUG-012 — The cart addition cannot be previewed and confirmed

- **Retest (run 5, since #31):** fixed. "Додати все в кошик Сільпо" now opens the API
  preview immediately; there is no local fill-in step. Confirmed by
  `tests/ui/specs/flows.spec.ts`.

- **Found in:** run 3 UI walk-through; confirmed by two `test.fail` checks in
  `tests/ui/specs/flows.spec.ts`.
- **Actual:** "Додати все в кошик Сільпо" immediately fills the side cart panel (7 units,
  490 грн) and disables itself; no preview appears. "↥ Синхронізувати з Сільпо" then opens
  "Попередній перегляд додавання в кошик" (adding 490 грн to 35 грн, total 525 грн), but the
  dialog already says "Пропозиція застаріла. Створіть новий перегляд перед підтвердженням." and
  "Підтвердити додавання" stays disabled. "↻ Перерахувати кошик" resets the panel to the two
  invented butter packs.
- **Cause of the disabled button:** in fixture mode the preview is `fixtures/cart-preview.json`,
  whose `expiresAt` is `2026-09-07T12:00:00+00:00`;
  `apps/web/src/features/planner-results/components/CartFlow.tsx:23` marks it expired and `:74`
  disables confirmation.
- **Expected** ([product](../PRODUCT.md), "Real cart"): "Add to Silpo cart" → preview of the exact
  changes → "Confirm addition" → verified per-item outcome; nothing changes before confirmation.
- **Impact:** the confirmed cart addition, a central step of the demo story, cannot be shown.
- **Retest (run 5, since #27):** the stale preview is gone. "↥ Синхронізувати з Сільпо" gets a
  fresh preview from `/api/cart/preview`, and "Підтвердити додавання" ends in the receipt
  "Результат синхронізації" (`tests/ui/specs/flows.spec.ts`, desktop). Still open for Alina:
  "Додати все в кошик Сільпо" fills the panel before any preview. The panel is only local state
  until the confirmation; nothing is sent to the cart before it.

## BUG-013 — Public-deployment hardening

- **Found in:** run 3 load check and read-only security review.
- **Actual:**
  - Each `GET /api/context` without the session cookie creates a new server-side session
    (`services/api/src/smart_basket/routes/api.py:100-108`): 300 such requests created 300
    sessions in 0.6 s. Sessions, runs, previews and receipts are never evicted, and plan
    creation has no rate limit, so anyone can grow memory on a public URL.
  - The session cookie is `HttpOnly` and `SameSite=Lax` but not `Secure` (`routes/api.py:108`).
  - FastAPI's `/docs` and `/openapi.json` are public.
- **Expected for a public demo:** session and run expiry or caps, a basic rate limit and
  `Secure` cookies behind HTTPS.
- **Impact:** none locally; a public deployment can be exhausted, and a restart signs every viewer
  out (recovery steps in `deploy/README.md`).
- **Confirmed as sound:** runs, previews and exports are isolated per session (404 across
  sessions; 30 parallel sessions without a leak), the POST origin allowlist, the FatSecret callback
  token check with `hmac.compare_digest`, no provider tokens in status responses, and generic
  500 messages.

## BUG-014 — Stale generated API contract

- **Found in:** run 4, the retest after #20–#22.
- **Steps:** `& services/api/.venv/Scripts/python.exe services/api/scripts/export_contracts.py --check`.
- **Actual:** `Generated artifacts are stale: packages/contracts/openapi.json`. The live catalog and
  cart work in #21 and #22 changed the server without regenerating the contract.
- **Expected:** `--check` passes; regenerate with `export_contracts.py` and review the diff
  (`services/api/README.md`).
- **Impact:** frontend types and fixtures can drift from the API, and the CI backend job fails at
  this step even after BUG-004 is fixed.
- **Retest (run 5, `afe586e`):** fixed in `5fcd4b4` (Sofiia); `--check` reports 22 contract and
  fixture files current.

## BUG-015 — No cart panel below 1280 px

- **Retest (run 5, since #31):** fixed. Below the `xl` breakpoint the same cart panel renders
  in the page flow instead of the side column, so preview and confirmation are reachable at
  every width tested (Pixel 7 included). Confirmed by
  `tests/ui/specs/flows.spec.ts` on both projects.

- **Found in:** run 4, the retest of Alina's shared cart (`1a121e0`); confirmed by
  `tests/ui/specs/flows.spec.ts` (`test.fail` on the mobile project).
- **Actual:** after "Додати все в кошик Сільпо" the button turns into the disabled
  "Додано в кошик Сільпо". At 1280 and 1440 px the side panel "Смарт кошик Сільпо" with
  "↥ Синхронізувати з Сільпо" appears; at 1279, 1024 and 768 px and on a Pixel 7 there is no cart
  panel and no other way to preview or confirm the cart. The limit matches Tailwind's `xl`
  breakpoint.
- **Expected:** the cart and its preview and confirmation are reachable at every supported width
  (the design includes mobile layouts), for example as a drawer or a section of the page.
- **Impact:** phones, tablets and laptop windows under 1280 px cannot finish the cart flow; the
  recording has to use a wide window.

## BUG-016 — Over-budget plans can go to the cart

- **Retest (run 5, since #31):** fixed. "Додати все в кошик Сільпо" is disabled whenever the
  API's `canConfirmCart` is false, over budget included, and the existing budget warning
  explains why. Confirmed by `tests/ui/specs/flows.spec.ts`.

- **Found in:** run 4; confirmed by `tests/ui/specs/flows.spec.ts` (`test.fail`).
- **Actual:** with a budget of 100 UAH the result says "Бюджет перевищено на 390,00 грн.", yet
  "Додати все в кошик Сільпо" stays enabled and "↥ Синхронізувати з Сільпо" opens the preview.
  Commit `1a121e0` describes this as intended: "budget overrun no longer blocks adding (warning
  shown instead)".
- **Contract:** `docs/CONTRACTS.md` enables cart confirmation only for a complete plan within the
  budget and otherwise asks to disable it with an explanation. The API already refuses such
  previews with 409 (e2e `test_over_budget_plan_cannot_reach_the_cart`).
- **Decision needed:** keep the contract and disable adding with an explanation, or change the
  contract and the API together.
- **Impact:** once the UI calls the API (BUG-002), this path ends in a 409 the user does not expect.
- **Retest (run 5, since #27):** confirmed at runtime. With a budget of 100 UAH the plan from the
  API says "Бюджет перевищено на 110,00 грн.", and "Додати все в кошик Сільпо" stays enabled.
  "↥ Синхронізувати з Сільпо" sends `POST /api/cart/preview`, which the API refuses with 409
  `STALE_PLAN` ("A complete proposal within budget is required.", `retryable: false`). The page
  opens "Помилка синхронізації кошика Сільпо" with that English message inside the Ukrainian text
  and offers "Повторити синхронізацію", which can only fail again. The code `STALE_PLAN` also
  misnames the reason for the frontend (Rina).

## BUG-017 — `GET` on the FatSecret export actions is swallowed by `GET .../{export_id}`

- **Found in:** run 7, Schemathesis 4.26.1 (`--continue-on-failure`, 1360 cases), reproduced
  consistently across two runs; JUnit report
  `tests/contract/reports/junit-20260912T155003Z.xml`.
- **Where:** `services/api/src/smart_basket/routes/api.py`. Route registration order:
  `POST /fatsecret/exports/preview` (line 330), `POST /fatsecret/exports/confirm` (line 337),
  then `GET /fatsecret/exports/{export_id}` (line 345).
- **Actual:** `GET /api/fatsecret/exports/confirm` and `GET /api/fatsecret/exports/preview` both
  answer `404 {"code": "NOT_FOUND", "message": "Export not found in this session."}` instead of
  `405 Method Not Allowed`. Starlette matches routes in registration order; since no `GET` route
  has the literal path `.../confirm` or `.../preview`, the request falls through to the later
  `GET /fatsecret/exports/{export_id}` route, which treats "confirm"/"preview" as an `export_id`
  value and correctly reports it unknown.
- **Reproduce:**
  ```
  curl -X GET -H 'Cookie: smart_basket_demo=<session>' http://127.0.0.1:8000/api/fatsecret/exports/confirm
  curl -X GET -H 'Cookie: smart_basket_demo=<session>' http://127.0.0.1:8000/api/fatsecret/exports/preview
  ```
- **Expected:** `405 Method Not Allowed` with an `Allow` header listing `POST` (RFC 9110), matching
  BUG-010's existing 405 finding.
- **Impact:** low on the demo flow — nothing in the app sends `GET` to these paths — but a
  misdirected or scripted `GET` gets a misleading "not found" instead of "wrong method", and any
  future path that starts with a real export ID's shape would silently match the wrong handler.
- **Fix hint:** registration order does not help here — Starlette's router
  (`starlette/routing.py`, `Router.app`) returns the first route in its list whose path *and*
  method both match, so a later `GET /{export_id}` still wins over an earlier `POST /confirm`
  partial match regardless of order. `export_id` values are always shaped
  `demo-export-<32 hex chars>` (`core.uid("export")`); constrain the path parameter to that
  pattern (a regex path converter) so literal segments like `confirm`/`preview` fail to match
  the parameterized route and fall through to the real 405.

## BUG-018 — Per-day calorie stat read as a huge shortfall that wasn't real

- **Found in:** run 13, an overnight QA pass driven by a browser agent (Claude in Chrome)
  against the live deploy with the golden input (1800 UAH, 4 days, 3 people, 2000 kcal/person/day,
  vegetarian, one cat).
- **Where:** `apps/web/src/features/planner-results/components/MealPlan.tsx:126-172` (Polina's
  own file, rewritten in #31).
- **Actual:** the label said "Середня калорійність на день" ("average calorie content per day")
  followed by one number per day, but the number was the *average of that day's individual
  meals' kcal-per-serving* (e.g. `(420 + 680 + 760) / 3 = 620`), not the day's total. Next to a
  2000 kcal/person/day target, "620" reads as a planner that is wildly off, when the real daily
  total (420 + 680 + 760 = 1860) is within 7% of the target.
- **Impact:** Medium-looking false alarm — nothing was actually wrong with the plan's calories,
  but the mislabeled stat could make a working planner look broken during QA or, worse, during
  the recorded demo or to a judge reading a screenshot.
- **Fix (this branch):** sum the day's meals instead of averaging them, only when every meal in
  that day has a known `kcalPerServing` (a partial sum would understate the day and reintroduce
  the same confusion); label it "Калорійність на день (сума прийомів їжі на людину)" and append
  the requested target from `effectiveRequest.caloriesPerPersonPerDay` when set, so the number on
  screen is directly comparable to the number the user typed in.
- **Retest:** `tsc --noEmit` clean; `next build` clean; e2e 40/40; Playwright UI 24/24 (desktop +
  mobile), all against a locally rebuilt stack with this change.
- **Not fixed (separate, pre-existing, documented limitation):** Sofiia's synthetic fallback meals
  use fixed kcal-per-serving values and do not run the ILP optimization that would actually target
  `caloriesPerPersonPerDay` (`services/api/src/smart_basket/meals/synthetic.py:611`, comment:
  "synthetic fallback does not run ILP optimization"). That is why the daily total lands near
  ~1,860 regardless of the requested figure rather than exactly matching it — expected for the
  synthetic/demo data path, not something Polina's fix touches or should touch.

## BUG-019 — No real `GEMINI_API_KEY` on the live deploy

- **Found in:** run 13, same overnight pass. Sending a chat message ("бюджет 1500") on
  `https://p01--web--2n7f5yvrbnqy.code.run` replied "Чат недоступний: на сервері не налаштований
  ключ Gemini (GEMINI_API_KEY)." and did not change the plan.
- **This is not a new defect.** `services/api/src/smart_basket/agent/llm.py:17-22` raises exactly
  this when no key is present, and returning that message instead of crashing or silently no-oping
  is the intended, already-tested fallback (`docs/qa/test-results.md` run 5: "without
  `GEMINI_API_KEY` ... the reply names the missing key instead of a silent no-op";
  `docs/qa/submission.md`: "not exercised with a real API key in QA"). CI and every local run to
  date also has no key.
- **Impact:** chat cannot be shown working live in the recorded demo or in front of a judge,
  since no real Gemini key has ever been supplied to Polina to deploy.
- **Fix:** needs Uliana (chat module owner) to supply a real `GEMINI_API_KEY` (or confirm none is
  available for the submission). Once supplied, Polina adds it as a Northflank **runtime
  variable** on the `api` service (a redeploy is enough for a runtime variable — no rebuild
  needed, unlike `API_BASE_URL`) and retests `/api/chat` against the live URL.
- **Until then:** do not claim live chat in the video; either skip that segment or record it
  once against a key if one arrives before the deadline.
