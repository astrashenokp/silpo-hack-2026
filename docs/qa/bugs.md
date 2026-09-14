# Bug list

Final-integration defects found by Polina. Each author fixes her own module
([decision owners](../WORKFLOW.md#decision-owners)); Polina retests and updates the
status here. Results of each run are in [test results](test-results.md).

Severity: **Blocker** stops setup or the demo flow; **High** breaks a required
feature; **Medium** misleads the user or a reviewer; **Low** is cosmetic or
documentation.

First found on `main` @ `0ef7fbb` (September 11, 2026). The latest retest is **run 14 on the frozen
revision `main` @ `402bdcb`**, verified against the live deploy (e2e 40/40, UI 42/42). This list has
not yet been sent to the owners; Polina shares it with the team.

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
| BUG-019 | Low | The hosted API had no real `GEMINI_API_KEY`, so chat on the live deploy could not do anything | Uliana (chat module); Polina to add the runtime variable | **Key supplied Sep 13 and verified working** (run 16): all four planning intents parse and a budget change really replans. Still to do: add it as a Northflank runtime variable on the `api` service. Note the key is free-tier, **5 requests per minute** |
| BUG-020 | Medium | Below the `lg` breakpoint (<1024 px) the sidebar is `display:none` with no replacement control, so "Новий чат", the chat list and "Збережені у FatSecret" cannot be reached at all — same class of defect as BUG-015 | Polina (own file, `apps/web/src/app/page.tsx`) | Fixed on `feature/polina-qa-run14`; retested ✅ (run 14, UI 42/42) |
| BUG-021 | Medium | In demo mode any dietary restriction other than `peanut-free` makes every product unmatched ("No candidate passed dietary verification … lacked provider evidence"), so the basket comes back empty while the meal plan looks fine | Rina (matching + demo catalog evidence); scope decision with Sofiia | Open — deliberately not fixed by Polina, see below |
| BUG-023 | Medium | The chat error text claimed "на сервері не налаштований ключ Gemini (GEMINI_API_KEY)" for *every* interpreter failure, so an exceeded free-tier quota told the user (and a judge) that the server is misconfigured, which is false | Polina (own file, `apps/web/src/app/page.tsx`) | Fixed on `feature/polina-qa-run16`; retested ✅ (run 16, both with and without a key) |
| BUG-024 | Low | `handle_chat_message` catches every interpreter exception and returns one generic `chat_error`, so a rate limit, a network blip and a missing key are indistinguishable to the caller | Uliana | Open |
| BUG-022 | Medium | "Скасувати" in the cart preview leaves the plan marked as handed over: the add button stays disabled telling the user to confirm in a window that was just closed, and a failed receipt does the same | Polina (own file, `apps/web/src/app/page.tsx`) | Fixed on `feature/polina-qa-run15`; retested ✅ (run 15, UI 46/46) |
| BUG-025 | Blocker | Edamam Meal Planner returned HTTP 403 for every request, and `EDAMAM_SYNTHETIC_FALLBACK=false` on the live deploy meant this failed every plan for every user — production was fully down | Polina (own file, `services/api/src/smart_basket/meals/edamam.py`) | Fixed in #43; retested ✅ (run 17, live: e2e 40/40, UI 56/56) |
| BUG-026 | High | Live Edamam's English ingredient names (`chicken`, `red potatoes`, …) never match the catalog's vocabulary, so the basket was empty on every plan | Polina, in Sofiia's `services/api/src/smart_basket/demo.py` + `meals/edamam.py` (user-authorised) | Fixed in #48 (98%, run 20); narrowed further in #49 with a name-based fallback for the ~2% Edamam sends with no category at all ("fish broth", "cornflakes", "Guacamole") |
| BUG-027 | High | With live Edamam meals, slots got any recipe (a macaron filling as dinner, pizza bread as breakfast) and daily calories landed 65–71% over the target (4 960 / 5 131 kcal vs 3 000) | Polina, in Sofiia's `services/api/src/smart_basket/meals/edamam.py` (user-authorised) | Fixed in #46; live ✅ (run 19: 2 people × 2 days × 2 000 kcal → sensible slots, 2 028 / 1 960 kcal) |
| BUG-028 | Medium | Meal calories shown unrounded ("1 753,376 ккал/порція"), and a live Edamam plan dumps ~50 identical English lines "No catalog candidates were found." across the result | Polina (`apps/web/src/lib/format.ts`, `ProposedBasket.tsx`) | Fixed in #46; UI ✅ (run 19, 58/58); new strings confirmed in the live bundle |
| BUG-029 | High | A live Edamam plan failed outright when any selected recipe had an ingredient without a gram weight (e.g. "salt to taste"): 1 person × 1 day × 3 000 kcal failed twice with "Edamam ingredient is missing gram weight" | Polina, in Sofiia's `services/api/src/smart_basket/meals/edamam.py` (user-authorised) | Fixed in #47; retested ✅ live (run 19: same input completed twice, once with a "Jalapeno left out" warning instead of failing) |
| BUG-030 | Medium | With no calorie target, live Edamam has no calorie floor and breakfast has no dish filter: one plan served a juice for breakfast (197 kcal), a recipe literally titled "Tst" for lunch (83 kcal), ~583 kcal for the day | Sofiia (meal-planning rules) | Open — the demo's golden input sets a calorie target, so not demo-blocking |
| BUG-031 | High | `cart_confirmable()` and `DemoCartService._check_products` both refused ANY plan whose `dataMode` was "mixed" (live Edamam meals + demo catalog) — even a perfectly complete, in-budget, fully-resolved plan — so the cart could never be confirmed once live Edamam meals shipped, regardless of match quality | Polina, in Uliana's `agent/orchestrator.py` + `cart/service.py` (user-authorised, explicit "post relax this" direction) | Fixed in #50; live ✅ (run 22: 13/13 products, preview 200, confirm 200/success) |
| BUG-032 | Medium | The CartPanel's "Синхронізувати з Сільпо" button stayed clickable after a plan's cart was already confirmed; clicking it hit 409 `STALE_PLAN`, and the error modal's own "retry" button called the same handler, trapping the user in a repeating "Помилка синхронізації кошика Сільпо" with no way out | Polina (own file, `apps/web/src/app/page.tsx`) | Fixed in #51; retested live — the disabled state alone gave no reason, extended in BUG-033 |
| BUG-033 | Low | The now-correctly-disabled Sync button (BUG-032) gave no reason for being disabled — reported live as "кнопка синхронізації не натискається" (the button doesn't respond), reading as broken rather than as intentional | Polina (own files, `CartPanel.tsx` + `page.tsx`) | Fixed on `feature/polina-sync-disabled-reason`; UI 60/60, e2e 40/40 |
| BUG-034 | Blocker | The 21:25 commit `61d857f` ("preserve arbitrary live ingredients") removed the demo-catalog fallback for connected Silpo accounts entirely: `SessionCatalog._search()`/`_search_live()` returned `[]` on no branch, no live match, or any live-search exception, and `prepare_requirements()` discarded a requirement's category search term, so a connected account with an active cart could still end up with nothing to match against — reported live as "нічого не може підібратися" | Polina, in Rina's `catalog/live.py` (user-authorised, second explicit override tonight after BUG-031) | Fixed on `feature/polina-live-search-demo-fallback`: restored `self.demo.search_products(...)` as the fallback in all three no-live-result paths, and `prepare_requirements()` now keeps both the ingredient name *and* its original category term as search terms so the demo category bucket can still be found. `get_product_details()` also still routed purely on `_live(owner)` instead of on whether the specific product id was demo-sourced, throwing `KeyError` for a connected owner's demo-fallback candidate — fixed to check the live cache first and fall back to `self.demo`, mirroring the pattern `check_restrictions()` already used (keyed on `product.source`, not the owner). 6 tests in `test_live_cart.py` updated for the restored contract; full suite 298/298 ✅; `tsc --noEmit` clean |
| BUG-035 | Medium | The frontend `ERROR_TEXT` map hardcoded Silpo-specific blame text for `RATE_LIMITED`/`UPSTREAM_UNAVAILABLE`, but both codes are raised by Edamam, FatSecret and Silpo backends alike (`agent/orchestrator.py`, `fatsecret/export.py`, `cart/service.py`) — reported live as "ФЕТ СІКРЕТ ПИШЕ ЩО СІЛЬПО ТИМЧАСОВО НЕ ПРАЦЮЄ", i.e. a genuine FatSecret-side failure was shown as a Silpo outage | Polina (own file, `apps/web/src/app/page.tsx`) | Fixed on `feature/polina-live-search-demo-fallback`: both messages reworded to name "зовнішній сервіс" instead of Silpo specifically. Note: this only fixes the mislabeling — the underlying FatSecret write failure it was masking is still open, see BUG-036 |
| BUG-036 | High | Live FatSecret Saved Meal export for a connected account fails with `UPSTREAM_UNAVAILABLE` (surfaced by BUG-035's mislabeled text as a Silpo outage) — confirmed live tonight that Silpo itself is fine and FatSecret specifically is failing, but `FatSecretClientError`/write-verification failures in `fatsecret/export.py` don't preserve or surface the underlying FatSecret provider message, so root cause (quota/rate limit vs. a malformed `saved_meal_item.add` write vs. an expired token) could not be diagnosed from the client alone; no server-log access from this session | Uliana / Polina (`fatsecret/export.py`, `fatsecret/matching.py`) | Open — needs the actual FatSecret provider error message (Northflank logs or a Claude-in-browser check, as used for the earlier `FATSECRET_ALLOW_EDAMAM_EXPORT` root cause) before a fix can be scoped |

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

## BUG-020 — The chat list is unreachable below 1024 px

- **Found in:** run 14, overnight browser-agent pass (the agent's viewport was ~785 px wide and it
  could not open a new chat at all; confirmed independently in Playwright: at 785 px the
  "+ Новий чат" button resolves to 0 visible elements).
- **Where:** `apps/web/src/app/page.tsx`. The `<aside>` held `hidden … lg:flex`, and the
  `lg:hidden` header cluster offered only the FatSecret bookmark and the demo badge — no control
  that could reveal the sidebar.
- **Actual:** under 1024 px "Новий чат", the whole chat list and "Збережені у FatSecret" are
  `display:none` with nothing to replace them, so a phone or a narrow laptop window cannot start
  a second chat, return to an earlier one, or open saved meals.
- **Impact:** Medium. Exactly the class of defect as BUG-015 (cart panel unreachable when narrow),
  which the contract treats as a real failure rather than cosmetics. It also silently blocked the
  QA pass's D3 scenario, so plan persistence between chats could not be checked at all.
- **Fix (this branch, additive only):** the sidebar markup and its contents are untouched. Added a
  "Чати та меню" toggle to the existing `lg:hidden` header cluster, a `menuOpen` state, a
  dismissable backdrop, and off-canvas classes so the same `<aside>` slides in as a drawer below
  `lg`; at `lg` and above every original class still applies and nothing new renders. Choosing a
  chat, creating one, or opening saved meals closes the drawer.
- **Retest:** UI suite 42/42 (desktop + Pixel 7) including four new checks — the chat list is
  reachable at both sizes, the drawer closes from the backdrop, the desktop layout is unchanged
  (no menu button, no backdrop), the full plan flow still completes at 390 px, and the document
  never scrolls sideways with the drawer open or closed. e2e 40/40.

## BUG-021 — Any restriction except `peanut-free` empties the basket in demo mode

- **Found in:** run 14. Selecting "Без молочного" + "Без глютену" + "Вегетаріанське" produced a
  normal meal plan but a basket where every line failed with "No candidate passed dietary
  verification (0 failed, N lacked provider evidence)" and confirmation was unavailable.
- **Where:** `services/api/src/smart_basket/demo.py:60-63`:
  ```python
  def check_restrictions(self, product, restrictions):
      if set(restrictions) - {"peanut-free"}:
          return "unknown"
      return product.restriction_check
  ```
  The demo catalog carries composition evidence for `peanut-free` only. Everything else returns
  `"unknown"`, and `catalog/matching.py:37-46` then correctly refuses to treat an unverified
  product as safe ("Never infer safety from a product name").
- **This is the safety design working, not a crash.** `GET /api/filters` still offers those
  labels, so the interface invites a choice the demo data cannot back with evidence.
- **Measured against the running API** (1 person, 1 day, UAH 1,800, one restriction at a time):

  | Restriction | `budgetStatus` | Products |
  |---|---|---|
  | `peanut-free` | `within_budget` | matched |
  | `gluten-free` | `incomplete` | none, `unresolvedRequirements` populated |
  | `dairy-free` | `incomplete` | none, `unresolvedRequirements` populated |

  So **1 of the 10 restrictions `/api/filters` offers works in demo mode; the other 9 empty the
  basket**. The five *preference* labels (`vegetarian`, `vegan`, `paleo`, `high-fiber`,
  `high-protein`) never reach `check_restrictions` and are unaffected — which is why other
  multi-label combinations in the same run still produced a basket, and why the demo script's
  golden input ("shared vegetarian meals") is safe as written.
- **Impact:** Medium, and demo-visible: a judge who picks a common restriction gets an empty
  basket. It does not affect the live Silpo catalog path, where real composition evidence exists.
- **Deliberately not fixed by Polina.** The fix is a dietary-safety decision in Rina's module, not
  an integration detail: making these products pass means asserting real composition claims
  (and "gluten-free oats" is genuinely contested because of cross-contamination). Inventing that
  evidence is the same class of fabrication as BUG-006/BUG-011 and is what the fail-closed design
  exists to prevent.
- **Fix options for the owner (pick one, do not silently widen `check_restrictions`):**
  1. Give the synthetic products explicit, defensible labels (dry rice and lentils really are
     vegetarian, vegan, dairy-free and gluten-free; leave oats out of the gluten-free claim) and
     let `check_restrictions` answer from that evidence per label.
  2. Or restrict `GET /api/filters` in demo mode to the labels the demo catalog can actually
     verify, so the interface never offers a choice that must fail.
- **Demo guidance until then:** in the recorded walkthrough use either no restriction or
  `peanut-free`; do not pick gluten/dairy/vegetarian restrictions on the demo data path.

## BUG-022 — Cancelling the cart preview leaves the plan stuck as "handed over"

- **Found in:** run 15, the second overnight browser-agent battery. Reported as "«Скасувати» не
  завжди повністю скасовує стан додавання"; reproduced exactly in Playwright.
- **Where:** `apps/web/src/app/page.tsx`. `addPlanToCart` marked the conversation item
  `added: true` before opening the preview, and the modal's `onCancel` only did
  `setCartPreview(null)`. `PlannerResults` computes `addDisabled={added || dirty || blocked}`
  and shows "Товари цього плану передані в кошик Сільпо; підтвердьте додавання у вікні
  перегляду."
- **Actual:** after pressing only "Скасувати" — nothing confirmed, nothing sent to Silpo — the
  "Додати все в кошик Сільпо" button stays permanently disabled for that plan, under a note
  telling the user to confirm in a window that was just closed. The same dead end followed a
  `failed` receipt, whose own error text asks the user to create a new preview they cannot open.
- **Impact:** Medium and demo-visible: one stray "Скасувати" makes that plan un-addable for the
  rest of the session. The only way out was the cart panel's separate sync control, which is not
  what the message points at.
- **Fix (this branch):** the preview now remembers which conversation item opened it
  (`cartSource`); dismissing it clears that item's `added` mark unless a receipt exists, so
  cancelling truly cancels. A failed receipt goes through the same path. A *successful*
  confirmation still keeps the plan marked as handed over, which is correct.
- **Retest:** UI 46/46 (desktop + Pixel 7), e2e 40/40, `tsc` and `next build` clean. Two new
  permanent checks: cancelling re-enables adding and removes the note, then the plan can be added
  and confirmed for real; and a confirmed plan stays disabled.

## BUG-023 — The chat error blamed a missing key for every failure

- **Found in:** run 16, the first run with a real `GEMINI_API_KEY`. The suite's own chat check
  started failing precisely because the app answered for real; re-running it alone "passed" only
  because the free-tier quota had been used up and the app fell back to the same message.
- **Where:** `apps/web/src/app/page.tsx` (Polina's file since #31). The `chat_error` branch
  returned "Чат недоступний: на сервері не налаштований ключ Gemini (GEMINI_API_KEY)."
- **Actual:** the API answers `chat_error` for *any* interpreter failure (BUG-024). Once a real
  key exists, the most likely one is an exceeded quota — the free tier allows **5 requests per
  minute** — so a guest, or a judge, who sends a sixth message in a minute is told the server has
  no key configured. That is a false statement about our own deployment, in front of the people
  scoring it.
- **Fix (this branch):** the message no longer asserts a cause it cannot know: "Не вдалося
  обробити запит: сервіс ШІ зараз недоступний (можливо, перевищено ліміт запитів). Спробуйте ще
  раз за хвилину." True whether the key is missing, rate-limited or briefly unreachable, and it
  tells the user what to do.
- **Also fixed here:** `tests/ui/specs/flows.spec.ts` asserted that exact key-related string, so
  the check only passed on a deployment *without* a key and would have broken CI the moment
  anyone added one. It now accepts any real answer — a replanned budget or a clearly worded
  unavailable message — and only fails on silence.
- **Retest:** with a key and without it, both: e2e 40/40 (2 chat tests skip by design when a key
  is present) and UI 46/46.

## BUG-024 — Every interpreter failure looks the same to the caller

- **Where:** `services/api/src/smart_basket/agent/orchestrator.py:530-544`. `handle_chat_message`
  wraps `interpret()` in `except Exception` and always returns the same `chat_error` payload.
- **Actual:** a missing key, an exceeded quota (HTTP 429, which the SDK raises as
  `RateLimitError` and which the free tier hits after 5 requests a minute), a network blip and a
  malformed model response are indistinguishable to the frontend, which therefore cannot say
  anything specific or decide whether retrying is worthwhile.
- **Measured:** with a valid key, `interpret()` succeeded for `change_budget`, `reduce_cost` and
  `replace_ingredient`, then raised `RateLimitError: Error code: 429 … limit: 5, model:
  gemini-3.7-flash … Please retry in 32.9s`. Waiting a minute restored it.
- **Impact:** Low on its own, but it forced BUG-023: the UI had to guess a cause. It also hides a
  retryable condition behind a permanent-sounding error.
- **Fix hint for the owner:** distinguish at least "no key configured" from "temporarily
  unavailable, retryable" (429 and transport errors) and pass that distinction out, so the client
  can offer a retry instead of inventing an explanation.

## BUG-025 — Edamam Meal Planner returned 403, taking production fully down

- **Found in:** live verification, September 13–14. `POST /api/plans` on
  `https://p01--web--2n7f5yvrbnqy.code.run` completed with
  `{"code":"UPSTREAM_UNAVAILABLE","message":"Edamam returned HTTP 403.","retryable":true}` for
  every request. `SMART_BASKET_MEALS_SOURCE=edamam` and `EDAMAM_SYNTHETIC_FALLBACK=false` were
  both live, so nothing masked the failure — no plan could be created for anyone, guest or
  connected.
- **Where:** `services/api/src/smart_basket/meals/edamam.py`,
  `EdamamMealPlannerClient.request_plan`. Put `account_user` in the URL where the Edamam **app
  ID** belongs, and sent `app_id`/`app_key` as query parameters instead of HTTP Basic Auth.
- **Expected:** the Meal Planner v1 contract: app ID URL-encoded into the path,
  `Authorization: Basic {app_id}:{app_key}`, `?type=public`, account user in the
  `Edamam-Account-User` header.
- **Fix (#43, Polina):** corrected to the documented contract. Added
  `test_edamam_client_uses_current_meal_planner_auth_contract`, which captures the real outgoing
  `Request` object and asserts the URL, the Basic Auth token, and that the app key never leaks
  into the URL.
- **Retest:** backend suite 222/222 before merge; live afterward, `POST /api/plans` now returns
  real Edamam recipes (`"Tuscan Roasted Chicken Recipe with Roasted Potatoes"`, `source:
  "edamam"`) instead of failing — confirmed the 403 itself is gone. Immediately surfaced BUG-026.

## BUG-026 — Live Edamam meals leave every basket empty (0 products)

- **Found in:** live verification right after BUG-025 (fixing the Edamam 403 — see below) was
  confirmed working: once Edamam succeeds, every plan comes back with
  `selectedProducts: []` and `budgetStatus: incomplete`.
- **Where:** the mismatch is between `services/api/src/smart_basket/meals/normalization.py`
  (Sofiia — generates `search_terms` straight from Edamam's English ingredient names, e.g.
  `chicken`, `red potatoes`, `extra virgin olive oil`) and
  `services/api/src/smart_basket/catalog/matching.py` /
  `services/api/src/smart_basket/catalog/live.py`'s `QUERY_ALIASES` (Rina — only ever knew
  three hardcoded terms: `oats`, `rice`, `lentils`, the exact vocabulary of the *synthetic*
  meal source).
- **Actual:** measured live — 0 of 49 ingredient requirements matched on 2 separate plans.
  This is not demo-catalog-specific: the live Silpo catalog is in Ukrainian and has no
  translation step for arbitrary English ingredient names either, so a connected real account
  would very likely see the same empty-basket outcome.
- **Impact:** Blocker for the basket/cart half of the product the moment live Edamam meals are
  on — a real meal plan with a permanently empty, unconfirmable cart.
- **Decision, September 13:** first reverted `SMART_BASKET_MEALS_SOURCE` back to `synthetic` on
  the live deploy so the basket kept working.
- **Decision revisited, September 14:** flipped back to `SMART_BASKET_MEALS_SOURCE=edamam` for
  the submission — realistic recipe names were judged more important than a working demo basket.
  Accepted consequence: the basket is empty and unconfirmable on the live deploy right now; the
  recorded demo must skip the Silpo-cart segment on the guest/demo path (see `demo-script.md`).
  The cart flow itself is not broken — it was fully verified end to end (preview, confirm,
  per-item read-back) on run 17 while meals were still synthetic.
- **Fix hint for the owner:** before this can be both real and cart-usable, ingredient search
  terms need either a translation step (English → Ukrainian) before hitting Silpo, or a
  broader/fuzzier catalog search than exact `QUERY_ALIASES` lookups. Sofiia and Rina to decide
  which side owns the mapping.

## BUG-027 — Live Edamam ignored meal slots and calorie targets

- **Found in:** run 19, the live site right after `SMART_BASKET_MEALS_SOURCE=edamam` went back on.
  A 2-day plan with a 3 000 kcal target served "Pepperoni Pull-Apart Pizza Bread" for breakfast
  (1 753 kcal per serving), "Pizza Margherita" for lunch and "White Chocolate Ganache Macaron
  Filling" for dinner; day totals were 4 960 and 5 131 kcal.
- **Where:** `services/api/src/smart_basket/meals/edamam.py`, `build_edamam_payload`. Every
  section was sent empty (`"Breakfast": {}, "Lunch": {}, "Dinner": {}`); only a plan-level
  calorie fit was set. The per-slot targets (25/35/40 %) were already computed in
  `nutrition.py` for display but never sent to Edamam.
- **Expected:** Edamam's documented meal-planner contract filters each section with
  `accept.all: [{"meal": [...]}, {"dish": [...]}]` and can bound it with its own `fit`.
- **Fix:** Breakfast accepts `meal: breakfast`; Lunch and Dinner accept `meal: lunch/dinner`
  and main-meal dishes only (`main course`, `salad`, `soup`, `pasta`, `pizza`, `sandwiches`,
  `seafood` — no desserts, sweets, ice cream or preps). Each section gets an `ENERC_KCAL` fit
  around its share of the daily target, ±35 % so a slot stays satisfiable; the ±10 % plan-level
  fit still bounds the day. Values taken from Edamam's documented enums.
- **Tests:** two new backend tests (per-section meal/dish filters; per-section calorie bands,
  including that a 1 753 kcal breakfast falls outside the band for a 3 000 kcal day). Backend
  224/224.
- **Not verifiable locally:** the Edamam credentials exist only on Northflank, so the new
  request shape cannot be tried against the real API before deploy. If Edamam cannot satisfy a
  stricter section, `collect_assignments` raises `EdamamUnavailable`; with
  `EDAMAM_SYNTHETIC_FALLBACK=false` that fails the plan outright. Set it to `true` before
  merging, then check a few live plans.

## BUG-028 — Unrounded calories and an English wall of unmatched ingredients

- **Found in:** run 19, same live plan.
- **Where:** `apps/web/src/lib/format.ts` (`formatServing` kept up to 3 decimals) and
  `apps/web/src/features/planner-results/components/ProposedBasket.tsx` (`UnresolvedList`
  printed every requirement with the raw English API reason).
- **Fix:** calories per serving are rounded to whole kcal. The unmatched block now leads with a
  count ("Не вдалося підібрати позицій: N") and the confirmation note; the list sits in a
  `<details>` that opens by default only for five items or fewer, and known API reasons are
  translated (unknown ones still shown verbatim, nothing hidden).
- **Tests:** new UI check shapes a real API result into 8 unmatched items with 1 753.376 kcal and
  asserts the count heading, a collapsed list, the Ukrainian reason, no English reason text and
  "1 753 ккал/порція". UI 58/58 (desktop + Pixel 7).

## BUG-029 — One ingredient without a gram weight failed the whole live plan

- **Found in:** run 19, live, right after #46 deployed. `POST /api/plans` with 1 person, 1 day and
  a 3 000 kcal target ended `failed` twice in a row with
  `{"code":"UPSTREAM_UNAVAILABLE","message":"Edamam ingredient is missing gram weight; conversion is unresolved."}`.
  It failed instead of falling back, which also shows `EDAMAM_SYNTHETIC_FALLBACK` was still
  `false` on the deploy at that moment.
- **Where:** `services/api/src/smart_basket/meals/edamam.py`, `_ingredient_amount` raised
  `EdamamUnavailable` for any ingredient whose `weight` was missing or zero. Edamam recipes often
  carry such items ("salt to taste", water), so one of them aborted every meal of the plan.
- **Honest note on cause:** a latent defect, but #46 is what exposed it for this input — the new
  per-section filters made Edamam choose different recipes. The same input completed before #46
  (with the pizza-bread breakfast BUG-027 describes).
- **Fix:** an ingredient without a positive gram weight is left out of shopping quantities and
  named in a plan warning ("… ingredient(s) without a gram weight left out of shopping quantities
  (salt)"). A recipe with no weighed ingredient at all still fails, since nothing could be bought
  for it.
- **Tests:** two new backend tests (a zero-weight "salt to taste" is skipped with a warning and the
  plan maps; a recipe whose every ingredient lacks weight still raises). Backend 226/226.

## BUG-030 — Without a calorie target, live Edamam picks near-empty or junk meals

- **Found in:** run 19, live. 1 person, 1 day, no calorie target: breakfast "Orange Turmeric
  Immunity Boosting Juice" (197 kcal), lunch a recipe titled "Tst" (83 kcal), dinner a quiche
  (303 kcal) — about 583 kcal for the whole day.
- **Why:** `build_edamam_payload` only sends calorie fits when a target is given, and Breakfast is
  filtered by `meal: breakfast` alone (no `dish` filter), so drinks qualify. Edamam's public
  recipe data also contains test-like entries such as "Tst" that pass the lunch filters.
- **Impact:** Medium, not demo-blocking — the golden demo input sets 2 000 kcal. Visible to anyone
  who leaves the calorie field empty.
- **Fix options for the owner:** send a default per-section calorie band when no target is given
  (or require a target for live Edamam), add a breakfast `dish` filter that excludes `drinks`,
  and drop recipes whose label is implausibly short.

## BUG-026, resolved — category-based matching for live Edamam ingredients

- **Approach:** Edamam tags every ingredient with a `foodCategory` (already carried as the second
  entry in `search_terms`, see `meals/edamam.py:_search_terms`) — a bounded taxonomy of roughly
  25 values, unlike ingredient names themselves, which are effectively unlimited. `demo.py` now
  ships 19 generic, clearly-labeled synthetic products ("Demo poultry, 500 g", "Demo condiments
  and sauces, 200 g", …) keyed by these category strings, so `find_product_candidates` — unchanged
  — matches on category exactly the same way it always matched `oats`/`rice`/`lentils`.
- **Measured, not assumed:** collected real `foodCategory` values across 145 live ingredients (4
  plans, run 20) before choosing the bucket list, then re-verified against 3 **fresh** live plans
  the fix had never seen: **115 of 117 real ingredients (98%) now resolve**, up from 0. The two
  that did not (`fish broth`, `Guacamole`) carried no category from Edamam at all — a residual,
  honestly-disclosed gap this approach cannot close, not a bug in the fix.
- **Dietary honesty preserved:** unlike oats/rice/lentils, these category placeholders carry no
  composition evidence and are deliberately left out of `restriction_labels`, so any requested
  restriction still fails closed to "unknown" (same as BUG-021) — only unrestricted requirements
  can select one. Covered by a dedicated test.
- **Scope:** this fixes the **guest/demo** path only (`SessionCatalog` routes here whenever no
  Silpo account is connected — this is what every QA run and the planned recording use). A
  connected real Silpo account still searches the live Ukrainian catalog directly with Edamam's
  English terms and was not touched; BUG-026's original note about that path likely having the
  same problem stands.
- **Tests:** parametrized over every category bucket (each alias resolves), case-insensitivity,
  restriction fail-closed behaviour, and a realistic 9-ingredient live-shaped set (8/9 resolve,
  matching the one genuinely uncategorized case). Backend 257/257 (was 226). e2e 40/40, UI 58/58
  locally.

## BUG-026, narrowed further — a name-based fallback for the last ~2%

- **Found in:** run 21, live, right after the new Edamam application key was applied. A 2-day
  plan with real recipes resolved 17 of 19 ingredients; the 2 unresolved ("fish broth",
  "cornflakes") had no `foodCategory` from Edamam at all, so #48's category matching had nothing
  to key off — a `budgetStatus: incomplete` plan the cart correctly refused to preview, exactly
  the safety behaviour BUG-016 established, not a new defect.
- **Fix:** `meals/edamam.py`'s `_search_terms` now guesses a category from the ingredient name,
  but only when Edamam sends none, and only for name patterns actually observed missing a
  category live (broth/stock/bouillon → the existing "canned soup" bucket; cornflakes/cereal/
  muesli/granola → "grains"; guacamole/salsa/hummus/pesto/dip → "condiments and sauces"). A real
  Edamam-provided category is never overridden, and an ingredient matching no pattern is left
  exactly as before — this narrows the known gap, it does not claim to close it.
- **Tests:** a real category from Edamam is kept as-is; each observed name pattern resolves to
  the right existing bucket; a name that merely contains a hint word is not reclassified when a
  real category is already present; a genuinely unrecognised, uncategorised ingredient is left
  alone. Backend 268/268 (was 257).

## BUG-031 — "Mixed" data mode unconditionally blocked cart confirmation

- **Found in:** run 21, live, right after BUG-026's category matching was confirmed working end
  to end (13/13 products, 0 unresolved, within budget). `canConfirmCart` was still `false`.
- **Root cause:** two independent, deliberately written and tested guards, not a bug in the
  usual sense:
  - `agent/orchestrator.py`'s `cart_confirmable()` required `uses_live_catalog or data_mode ==
    "demo"` — `data_mode` becomes `"mixed"` whenever meals come from Edamam, regardless of how
    the products resolved, so this returned `false` unconditionally for every live-Edamam plan.
  - `cart/service.py`'s `DemoCartService._check_products` separately required `plan.data_mode ==
    "demo"`, refusing `/cart/preview` with `DEMO_ONLY` even if the first check had passed.
  - A dedicated test, `test_uliana_marks_edamam_meals_as_mixed_and_blocks_demo_cart`, confirms
    this was intentional, tested design — not an oversight.
- **Why it no longer holds:** `data_mode` reports the *meal* source (live/demo/mixed); it says
  nothing about the *product* source, which is the only thing that actually determines which
  cart-write path (live Silpo vs demo) is safe to use. A plan with live Edamam meals but
  exclusively synthetic products is exactly as safe to write through the demo cart service as a
  fully-synthetic plan — the case this guarded against (writing demo product IDs through the live
  path) cannot happen, since that path is only ever taken when every product's source is
  `"silpo"`.
- **Decision, September 14 (Polina, explicit):** relaxed both checks to key off product source
  instead of `data_mode`. `data_mode` keeps reporting "mixed" for display (the DemoBadge, the
  warning text) — the disclosure stays fully honest — only the confirmability decision changed.
  This reverses tested, intentional behavior from another module; flagged here in full for
  Uliana and Rina to review after the deadline.
- **Fix:**
  - `cart_confirmable()`: added `uses_demo_catalog` (all products `"synthetic"`) alongside the
    existing `uses_live_catalog`; the rule is now `uses_live_catalog or uses_demo_catalog`. A
    genuinely incoherent mix of product sources in one basket is still refused.
  - `DemoCartService._check_products`: dropped the `plan.data_mode != "demo"` clause; kept the
    `any(p.source != "synthetic" ...)` guard.
  - Both warning strings ("cart confirmation is disabled") corrected to state only what remains
    true (mixed data sources), since it is no longer accurate that confirmation is disabled.
- **Tests:** the existing intentional-behavior test renamed and its assertions flipped to the
  new contract (`canConfirmCart: true`, `/api/cart/preview` → 200). Added a direct parametrized
  unit test of `cart_confirmable()` covering demo, mixed+synthetic, live, mixed+live, a
  genuinely incoherent source mix (still refused), and an empty selection (still refused); plus
  budget/unresolved/cart-context-ready edge cases. Backend 275/275 (was 268).

## BUG-032 — Sync button kept failing after the cart was already confirmed

- **Found in:** run 22, live, right after BUG-031's fix let the very first confirm-to-cart
  succeed end to end. Reproduced immediately after: preview → confirm (200, success) → sync
  again on the same plan → 409 `STALE_PLAN`, `"This proposal already has a cart receipt; review
  that outcome."`
- **Where:** `apps/web/src/app/page.tsx`, the `cartPanel()` builder. `syncDisabled` only checked
  `!cartPlan || cartItems.length === 0` — nothing accounted for the plan already having a
  receipt. The resulting error modal's retry button (`onRetry={handleRetrySync}`) calls
  `requestPreview(cartPlan)` again when there is no open preview, i.e. the exact same call that
  just failed — so retrying could never succeed, only repeat the same error.
- **Fix:** `syncDisabled` also checks `cartReceipt !== null` — once a plan's cart is confirmed,
  the sync control disables, matching the main "Додати все в кошик Сільпо" button's existing
  behaviour (disabled via `added` since BUG-022). Nothing is lost: there is nothing left to sync
  for an applied plan.
- **Tests:** new UI check confirms the cart, then asserts the sync button is disabled and the
  error modal never appears. UI 60/60 (was 58), e2e 40/40, `tsc`/`next build` clean.

## BUG-033 — A correctly-disabled Sync button gave no reason

- **Found in:** live testing right after BUG-032 shipped. A silently disabled button (no visible
  message, no tooltip) reads as broken, not as "there is nothing to do here right now" —
  reported as "кнопка синхронізації не натискається!!".
- **Fix:** `CartPanel` takes an optional `syncDisabledReason` and shows it both as a `title`
  tooltip and as small text under the button whenever `syncDisabled` is true for a reason more
  specific than an empty cart. `page.tsx` supplies two concrete reasons: "Кошик уже
  підтверджено — синхронізувати більше нічого" (a receipt already exists, BUG-032's case) and
  "Спершу натисніть «Додати все в кошик Сільпо» у плані" (nothing has been added to the panel
  yet). Purely additive — `syncDisabled`'s own logic is unchanged.
- **Tests:** UI 60/60, e2e 40/40, `tsc`/`next build` clean.
