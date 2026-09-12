# Code review — whole repository

Reviewer: Polina, with Claude Code. Revision: `main` @ `cf7ebbf` (September 11, 2026, after PRs #26
and #27).

**Scope.** Every source file in `services/api/src` and `apps/web/src`, plus `services/api/pyproject.toml`,
`.env.example`, `apps/web/next.config.ts` and the deployment files. Generated contracts, fixtures
and the test suites were not reviewed line by line.

**Method.** The code was read and each finding traced to its lines. Findings marked **Reproduced**
were also run on September 11 against this revision, by calling the modules from the backend virtual
environment without changing any file. All other findings come from reading the code; live Silpo,
Edamam and FatSecret were not called.

**Owners** follow the git history of each file and [the roles](../roles/). Defects already in the
[bug list](bugs.md) are not repeated here; related ones are named in the findings. Severity uses the
bug list's scale: **High** breaks a required feature or risks a wrong real-world action,
**Medium** misleads the user or blocks a secondary path, **Low** is maintenance, polish or a latent
risk.

## Summary

| ID | Severity | Area | Finding | Owner | Evidence |
|---|---|---|---|---|---|
| CR-01 | High | Live cart | Failed Silpo cart reads return an empty cart, so a write can lower quantities already in the real cart | Rina, Arina | Reproduced |
| CR-02 | High | Restrictions | Fish-free and red-meat-free pass when a short keyword list finds nothing (pollock, ham pass) | Rina | Reproduced |
| CR-03 | High | Silpo context | A failed read of the user's saved food restrictions plans without them, with no warning | Arina, Rina | Reproduced |
| CR-04 | High | Recurring | Selecting any recurring purchase makes recalculation fail | Rina, Vika, Uliana | Reproduced |
| CR-05 | High | Agent | The chat agent has no HTTP route, the meal replanner is not connected, the chat box sends nothing | Uliana, Rina, Sofiia, Ksiusha, Alina | Reproduced (backend) |
| CR-06 | High | Result UI | The result shows two meals of day 1 and no product list; the complete views are never rendered | Alina, Ksiusha | Code |
| CR-07 | Medium | Cart UI | Quantities changed or items removed in the cart panel are not what gets previewed and written | Alina, Polina, Rina | Code |
| CR-08 | Medium | Cart UI | "Повторити синхронізацію" after a failed receipt can never succeed | Alina | Code |
| CR-09 | Medium | Live cart | A confirmation attempted while Silpo is disconnected leaves the preview stuck "in progress" | Rina | Reproduced |
| CR-10 | Medium | Live cart | An uncertain write leaves no receipt, and the retry is refused as `STALE_PLAN` | Rina | Code |
| CR-11 | Medium | Orchestration | Recalculated or replanned live plans lose `canConfirmCart`; the flag and the cart services disagree | Uliana, Rina | Reproduced |
| CR-12 | Medium | Silpo context | Any Silpo profile label outside the supported list makes every plan fail | Arina, Sofiia | Reproduced |
| CR-13 | Medium | Edamam | Live Edamam ingredients (English names, always grams) cannot be matched to Silpo products | Sofiia, Rina | Code |
| CR-14 | Medium | Operations | Planner, export and sign-in failures are swallowed without any log | Rina | Code |
| CR-15 | Medium | Sign-in | A denied or failed OAuth callback ends on a raw JSON page instead of the app | Arina, Rina | Code |
| CR-16 | Medium | Frontend API | Two API clients with different error types; session recovery exists only in the form | Ksiusha, Alina, Polina | Code |
| CR-17 | Low | Errors | Provider errors are classified by searching the message text for "401", "429" and similar | Rina, Arina | Code |
| CR-18 | Low | Performance | Every Silpo call opens a new MCP connection; planning makes many sequential calls | Arina, Rina | Code, not measured |
| CR-19 | Low | Labels | API description, `X-Data-Mode` and progress texts say "demo" on live paths | Rina | Code |
| CR-20 | Low | Errors | Every cart refusal is `STALE_PLAN`; the UI shows the English message | Rina, Alina | Code |
| CR-21 | Low | Form | The form replaces the server's validation message with "Спробуйте ще раз" | Ksiusha | Code |
| CR-22 | Low | Frontend | Unreachable fixture paths that fake plans, carts and exports are still in the code | Ksiusha, Alina, Sofiia | Code |
| CR-23 | Low | Accessibility, UI | Page language, buttons without actions, IDs instead of names, units, debug logs | Ksiusha, Alina, Katia | Code |
| CR-24 | Low | Hygiene | Stray script, an unpinned SDK, stale comments, global caches, dead branches | Uliana, Rina, various | Code |
| CR-25 | Low | Deployment | Both images run as root; the web image ships development dependencies | Polina | Code |

## Fixed after this review

[PR #31](https://github.com/astrashenokp/silpo-hack-2026/pull/31) ("connect the whole UI to the
Python API") closes the following, verified by the backend, e2e and UI suites on that branch:

| ID | What changed |
|---|---|
| CR-05 | `POST /api/chat` exposes the agent, `replan_meal_plan` is wired into the planner, and the chat box sends messages to it |
| CR-06 | The result screen renders the API plan through `MealPlan`, `ProposedBasket`, `BudgetSummary` and `RecurringSuggestions`; the invented cards, prices, images, name and store address are deleted |
| CR-07 | The cart panel mirrors the plan version that was added instead of offering edits the API ignores |
| CR-08 | A failed receipt now clears the preview, so the retry creates a new one |
| CR-11 | One `cart_confirmable` rule in all four orchestrator branches; a replanned live plan keeps its live data mode |
| CR-21 | The form shows the server's validation message |
| CR-22 | The fixture paths, `lib/api/fixtures.ts` and the brand image are removed |
| CR-20 (partly) | The interface maps API error codes to Ukrainian text; the API still answers several cart refusals with one `STALE_PLAN` code |
| CR-04 (guarded) | Selecting a recurring purchase still breaks recalculation in the API, so the interface shows the suggestions and disables the choice with that reason |

Everything else below is still open.

## High

### CR-01 — Failed Silpo cart reads return an empty cart

- **Where:** `services/api/src/smart_basket/mcp/adapters.py:832-850`. `get_current_cart` catches every
  exception and, through `_handle_adapter_exception` (`:468-477`), returns `{}` unless the message
  contains 401, 403, 429, 503, "unauthorized", "rate limit" or "unavailable". A tool error is turned
  into `McpReadError` (`:30-35`) and then also swallowed.
- **Effect in the cart service** (`services/api/src/smart_basket/cart/service.py`):
  - the preview builds its snapshot from that result (`:188-189`);
  - `before` defaults to 0, and the write sends the absolute `quantity: before + planned`
    (`:214-226`);
  - the confirmation re-reads the cart and compares it with the snapshot (`:300-302`), but two
    failed reads are both `{}` and match;
  - the read-back after the write (`:314`) is `{}` too, so every item is reported as failed.
- **Reproduced:** a timeout and a tool error both return `{}`.
- **Impact:** while the cart tool keeps failing, a product the user already has in the real Silpo
  cart (say 2 packs) can be set to the plan's quantity (1 pack). The receipt can also say "failed"
  after a successful write.
- **Fix hint:** in the cart paths every read failure must stop the operation. Keep "no active cart"
  (a valid answer) apart from "read failed", and never swallow `McpReadError`.

### CR-02 — Keyword composition checks pass fish-free and red-meat-free

- **Where:** `services/api/src/smart_basket/catalog/live.py:50-93`. When the provider gives no
  explicit label, `fish-free` and `red-meat-free` become "pass" if the composition contains none of
  about ten tokens (`:71-88`).
- **Missing from the lists**, for example:
  - fish: минтай, хек, тріска, скумбрія, сардина, шпроти, кілька, ікра;
  - red meat: шинка, бекон, сало, ковбаса, сосиски, смалець, желатин, generic "м'ясо".
- **Reproduced:** "філе минтаю, сіль" → `pass` for fish-free; "шинка варена, сіль" → `pass` for
  red-meat-free.
- **Contract:** `catalog/matching.py:38-43` says restricted requirements fail closed and safety is
  never inferred from names. The absence of a keyword is not a verification.
- **Impact:** a product with pollock or ham can be chosen for a household that excluded fish or
  red meat, and shown as passing the restriction.
- **Fix hint:** return "pass" only for an explicit provider label. A keyword hit may produce "fail";
  anything else is "unknown".

### CR-03 — Saved food restrictions are dropped when the read fails

- **Where:** `services/api/src/smart_basket/mcp/adapters.py`.
  - `get_food_restrictions` (`:794-800`) returns `[]` on any error that is not in the "critical" list.
  - `get_user_context` (`:857-864`) then builds the context without the user's restrictions and adds
    no warning.
  - Profile, family and purchase-history reads behave the same (`:479-495`, `:507-528`). A failed
    history read is reported as "Silpo purchase history is empty." (`:884-885`), although the module
    itself says a read failure "is different from a valid empty history" (`:15-16`).
- **Reproduced:** a timeout returns `[]` for both restrictions and purchase history.
- **Impact:** a connected user's saved allergens silently stop applying to meals and products.
- **Fix hint:** fail the context read, or keep going with a visible warning and treat the
  restrictions as unknown, so restricted matches fail closed.

### CR-04 — Selecting a recurring purchase makes recalculation fail

- **Where:**
  - `services/api/src/smart_basket/catalog/matching.py:45-46` raises
    `ValueError("Recurring candidate lookup awaits Vika's normalized requirements.")` whenever a
    selected recurring item is passed.
  - `UlianaPlanner.recalculate_plan` (`agent/orchestrator.py:1736-1807`) passes the selection
    straight in.
  - The worker turns the error into `PLANNER_FAILED`, 502 retryable (`routes/api.py:85-90`).
- **Reproduced:** a recalculation with one selected recurring item raises that `ValueError`.
- **Why it is hidden today:** the result screen shows fixed cards instead of `recurringItems`
  (BUG-011). `onToggleRecurring` is passed to `PlannerReadyView` but never used
  (`features/planner-results/PlannerResults.tsx:592-685`), so nobody can select an item yet.
- **Impact:** once BUG-011 is fixed, the restocking feature fails every time a connected user uses it.
- **Fix hint:** look up products for recurring items by `productId` or name, so the optimizer
  (`optimization/optimizer.py:66-91`) gets candidates. Until then, reject the selection with a 400
  before queuing.

### CR-05 — The chat agent and the meal replanner do not reach the product

- **Chat has no route:** `services/api/src/smart_basket/routes/api.py` has no chat route (checked on
  the running app), so `UlianaPlanner.handle_chat_message` (`agent/orchestrator.py:497-606`) is
  called only by tests.
- **The replanner is not connected:**
  - `app.py:35` creates `UlianaPlanner(app.state.catalog)` without `meal_replanner`.
  - "reduce cost", "upgrade" and "replace ingredient" therefore always return
    `meal_replan_required` (`orchestrator.py:94-96`, `:1170-1188`).
  - Sofiia's `smart_basket.meals.replan_meal_plan` already has the matching signature
    (`meals/planner.py:50-57`).
- **Reproduced:** `meal_replanner` is `None`, and no route contains "chat".
- **The UI sends nothing:** the chat box only appends the text to the local list
  (`apps/web/src/app/page.tsx:363-372`). Text typed on the welcome screen and the quick prompts only
  become the chat title (`page.tsx:264-274`).
- **Impact:** about 1,300 lines of Gemini chat orchestration and the replanner are invisible, and
  anything a user types in the chat is silently ignored.
- **Fix hint:**
  - pass `meal_replanner=replan_meal_plan`;
  - add a queued chat route that goes through the same result checks as `work()`;
  - decide how a budget change may alter `effectiveRequest`: `work()` rejects that today
    (`routes/api.py:70-71`);
  - wire the chat box, or hide it until then.

### CR-06 — The result screen hides most of the plan and the basket

- **Where:** `apps/web/src/features/planner-results/PlannerResults.tsx`.
  - `:624` renders only the first two meals of day 1; `:858` renders two ingredients per meal.
  - Ingredient rows carry fixed prices and images (`:893-934`, BUG-011).
  - The selected products with package quantities are not shown on the result at all. They appear
    only in the cart panel after "Додати все", at 1280 px and wider.
- **The complete views exist but are never shown:**
  - `PlannerForm.tsx:694-914` renders every meal, calories per day, warnings, ingredients and
    products. It is replaced at once, because `handlePlanReady` fills `chat.view` and the form is
    unmounted (`page.tsx:374-381`, `:518-523`).
  - These components are never rendered anywhere in the app: `MealPlan.tsx`, `ProposedBasket.tsx`,
    `BudgetSummary.tsx`, `RecurringSuggestions.tsx`, `EmptyHistoryBanner` in `states.tsx`,
    `components/ui/Button.tsx` and `components/ui/ProductImage.tsx`. The first four already use the
    source, restriction and data-mode badges.
- **Contract** ([QA and Demo](../QA_DEMO.md), [product](../PRODUCT.md)): meals by day with portions
  and calories, a basket with package quantities, the budget and labeled warnings.
- **Impact:** a 4-day, 3-person plan appears as two meals plus invented products. The video cannot
  show the planner's real output.
- **Fix hint:** render the result with `MealPlan`, `ProposedBasket`, `BudgetSummary` and
  `RecurringSuggestions`, which fixes BUG-011 at the same time, or reuse the form's completed view.

## Medium

### CR-07 — Cart panel edits are not what gets written

- **Where:** `apps/web/src/app/page.tsx`. The panel changes local quantities and removes items
  (`:383-406`), and merges products from several plans and chats (`:408-424`). The preview, however,
  is always requested for one whole plan version (`:426-435`). The API previews and writes that
  plan's `selectedProducts` with the plan's quantities (`cart/service.py:48-51`, `:192-226`).
- **Impact:**
  - removed items are still added;
  - changed quantities are ignored;
  - products from other chats are silently dropped.

  The preview dialog shows the API's list, which differs from the panel.
- **Note:** the choice of the last added plan (`cartPlan`) is Polina's wiring from #27.
- **Fix hint:** make the panel a read-only view of the plan being added. Otherwise the API needs an
  edited selection (product IDs and quantities, validated against the plan).

### CR-08 — Retrying a failed cart confirmation can never succeed

- **Where:** after a receipt with status `failed`, `page.tsx:459-463` keeps the same preview and
  idempotency key, and "Повторити синхронізацію" re-sends them (`:476-479`). Both cart services store
  the receipt per preview and return it again for the same preview (`cart/service.py:68-70`,
  `:270-273`), so the retry always shows the same failure.
- **Fix hint:** after a failed receipt, drop the preview and request a new one with a new key.

### CR-09 — A cart preview gets stuck "in progress" when Silpo is disconnected

- **Where:** `services/api/src/smart_basket/cart/service.py:289-294`. The preview is added to
  `live_cart_inflight` and the key is recorded before the connection check. `AUTH_REQUIRED` and
  `CART_CONTEXT_REQUIRED` are raised outside the `try/finally` that clears the in-flight mark
  (`:296-321`).
- **Reproduced:** the first confirmation returns `AUTH_REQUIRED`; after reconnecting, the same
  preview returns `CONFIRMATION_IN_PROGRESS` indefinitely (`:274-280`).
- **Fix hint:** check the connection before marking the preview, or move the checks inside the
  `try`.

### CR-10 — An uncertain live write leaves no receipt

- **Where:** if the read-back after the write fails with an error the adapters re-raise,
  `_provider_error` ends the request (`cart/service.py:314`, `:317-318`), and no receipt is stored.
  The retry re-reads the cart, which the first write has changed, and stops with `STALE_PLAN`
  (`:300-302`).
- **Contract:** an uncertain outcome is read back and reported to the user.
- **Impact:** the user is never told what was written.
- **Fix hint:** store an "uncertain" receipt with the snapshot and allow a read-only reconciliation
  of the same preview.

### CR-11 — Recalculated live plans lose `canConfirmCart`

- **Where:** `services/api/src/smart_basket/agent/orchestrator.py`.
  - `run_planner` allows confirmation for plans built on the live catalog (`:406-420`).
  - Three other places require `data_mode == "demo"`: `_build_updated_result`, used by
    `/recalculate` (`:960-971`); `_build_replanned_result` (`:1053-1068`); and
    `_handle_change_budget` (`:697-713`).
  - `_build_replanned_result` also re-derives the data mode from the meals only, and re-adds
    "catalog/cart data remains demo" to live plans (`:1021-1051`).
- **Two services, two rules:** the live cart service ignores `can_confirm_cart`
  (`cart/service.py:178-184`), while the demo one checks it (`:31`).
- **Reproduced:** recalculating a plan whose data mode is `live` gives `canConfirmCart: false`; the
  same plan in demo mode gives `true`.
- **Fix hint:** one helper for the confirmation rule, used in all four places, and a check of the
  flag in both cart services.

### CR-12 — Silpo profile labels outside the supported list fail every plan

- **Where:** `mcp/adapters.py:860-864` passes the profile's preference and restriction labels through
  unchanged; only "fish" and "red-meat" are mapped (`:96-104`). `meals/filters.py:105-123` then
  raises `UnsupportedMealFilter` for any label outside the 5 preferences and 10 restrictions, and the
  orchestrator reports `VALIDATION_ERROR` (`agent/orchestrator.py:265-271`).
- **Reproduced:** a context restriction `lactose-free` raises
  `Unsupported hard restrictions: lactose-free`.
- **Impact:** a connected user whose Silpo profile holds any other label cannot plan at all, and the
  error names a label the user never typed. Silpo's real label set has not been verified.
- **Fix hint:** map Silpo's vocabulary explicitly. Show unmapped profile labels as warnings and keep
  product matching fail-closed for them, instead of failing the run.

### CR-13 — Live Edamam ingredients cannot be matched to Silpo products

- **Where:**
  - `services/api/src/smart_basket/meals/edamam.py:218-229` gives every ingredient in grams, with
    its English name as the search term (`:344-349`).
  - Matching needs the same unit (`catalog/matching.py:69-72`, `:24-27`), but liquids and eggs in
    Silpo are sold in ml or pieces.
  - Ukrainian search aliases exist only for oats, rice and lentils (`catalog/live.py:114-118`).
  - Recipe details are fetched one by one with an 8-second timeout each (`meals/planner.py:111-114`).
- **Impact:** with `SMART_BASKET_MEALS_SOURCE=edamam` and Silpo connected, most requirements stay
  unresolved, so the plan is incomplete and cannot be added to the cart. A 14-day plan also needs
  up to 42 sequential recipe requests.
- **Fix hint:** translate or alias ingredient names for Silpo search, convert g to ml or pieces where
  a density or piece weight is known, and fetch recipes in parallel with a limit.

### CR-14 — Failures are not logged

- **Where:**
  - `routes/api.py:85-90` turns any worker exception into `PLANNER_FAILED` without logging it.
  - The generic handler in `app.py:84-87` is silent.
  - So are export failures (`fatsecret/export.py:321-329`) and sign-in failures
    (`routes/auth.py:20-21`, `:45-46`).
  - Only `mcp/adapters.py` uses `logging`.
- **Impact:** a failure during the live demo cannot be diagnosed from the server output. Run 1 needed
  code reading to find the cause of BUG-003.
- **Fix hint:** call `logger.exception` in these handlers and keep the generic client messages.

### CR-15 — OAuth errors end on a raw JSON page

- **Where:** `services/api/src/smart_basket/routes/auth.py:35-46` and `:92-127` raise `ApiError` on a
  denied, incomplete or failed callback. The callback is a browser navigation, so the user sees
  `{"error": …}` on the API address.
- **Unused helpers:** `return_url(connected=False)` in `mcp/oauth.py:121-126` and
  `fatsecret/auth.py:124-132` is never called, although the page already handles `?silpo=` and
  `?fatsecret=` on return (`page.tsx:173-187`).
- **Fix hint:** redirect to `return_url(connected=False)` with a reason code and show the message in
  the app.

### CR-16 — Two frontend API clients

- **Two clients:**
  - `apps/web/src/lib/api/client.ts:20-59` (`ApiError`);
  - `apps/web/src/lib/api/planner.ts:203-314` (`ApiClientError`, with its own copies of
    `PlanningRequest` and `RunSnapshot`).
- **Session recovery only in the form:** `isAuthError` recognizes only `ApiClientError`
  (`planner.ts:252-262`). After an API restart, the cart, FatSecret and recalculation actions show
  "Initialize a demo session with GET /api/context." (`routes/api.py:25`) instead of a reconnect
  prompt.
- **Polls never stop:** `pollRun` and `pollExport` (`client.ts:165-197`) have no time limit or
  cancellation, so a stuck run polls until the tab closes.
- **Fix hint:** one client and one error type, `AUTH_REQUIRED` mapped to a session-restore state
  everywhere, and polls with a deadline and an abort signal.

## Low

### CR-17 — Errors classified by message text

- **Where:** `routes/api.py:132-140` and `:175-183`, `cart/service.py:364-373`, and
  `mcp/adapters.py:453-457` and `:468-477` all decide the status by searching `str(exc)` for "401",
  "429", "unavailable" and similar.
- **Impact:**
  - An unrelated message containing these strings disconnects the account or changes the retry
    behavior.
  - A token-refresh failure whose text lacks them is reported as a retryable 502, while
    `silpo_connected` stays true.
- **Fix hint:** catch typed errors: HTTP status errors, the SDK's OAuth errors, MCP error codes.

### CR-18 — One MCP connection per call

- **Where:**
  - `mcp/connection.py:55-82` builds a new HTTP client, OAuth provider and MCP `initialize` for every
    `get_mcp_session`.
  - The live catalog opens one per search term, then reads details for up to six products one at a
    time (`catalog/live.py:153-185`).
  - The context makes about seven sequential tool calls (`mcp/adapters.py:853-879`), each with up to
    three attempts and one-second pauses (`:444-466`).
- **Impact:** slow live planning and a higher rate-limit risk. Not measured, because no live session
  was used.
- **Fix hint:** one MCP session per planning run, and bounded parallel detail reads.

### CR-19 — "Demo" labels on live paths

- **Where:**
  - The API description says "Synthetic fixtures only" (`app.py:29-30`).
  - `/api/health` always reports `mode: demo` (`schemas/__init__.py:68-70`).
  - The middleware sets `X-Data-Mode: demo` on every plan and cart response (`app.py:64`), even for
    a live or mixed result.
  - Progress ends with "Demo planning result is ready." (`routes/api.py:84`).
  - `.env.example:1` says planning still uses demo data.
- **Fix hint:** set `X-Data-Mode` from the result's `dataMode`, and update these texts.

### CR-20 — Every cart refusal is `STALE_PLAN`

- **Where:** `cart/service.py:31-32`, `:37`, `:40`, `:46`, `:169`, `:184`, `:195-198`, `:211-213` and
  `core.py:79` and `:85` all use `STALE_PLAN`, for:
  - an over-budget or incomplete plan;
  - a plan that already has a receipt;
  - a changed price or availability;
  - missing write coordinates;
  - an expired preview.

  The UI shows the English message inside Ukrainian text (`page.tsx:440-444`; BUG-016, run 5).
- **Fix hint:** distinct codes such as `OVER_BUDGET`, `INCOMPLETE_PLAN`, `ALREADY_APPLIED` and
  `PREVIEW_EXPIRED`, with Ukrainian texts chosen by code in the UI.

### CR-21 — The form hides the server's validation message

- **Where:** `features/planner-input/PlannerForm.tsx:504-519`. Any error from creating the plan,
  apart from an auth error, becomes "Не вдалося сформувати план. Спробуйте ще раз."
- **Impact:** the API's message (an unsupported label, for instance) is lost, and the form suggests
  retrying an error that is not retryable. A failed run does show its message (`:1228-1243`).
- **Fix hint:** show the API message and offer a retry only when the error is marked `retryable`.

### CR-22 — Unreachable fixture paths

- **Where:**
  - `page.tsx:61-106`, `:309-311` and `:1061-1111` (demo scenarios, local FatSecret preview and
    export) are reachable only from a fixture chat, and nothing creates one.
  - `page.tsx:498-511` retries a failed plan with `fixturePlanningRequest` instead of the user's
    input.
  - `PlannerForm.tsx:458-496` (`demoMode`).
  - `PlannerResults.tsx:81-101`, `:180-184` and `:350-422`: a timer "thinking" and a form whose
    fields are not connected to any state.
  - `demo.py:66-139` (`DemoPlanner`).
  - The cart panel shows two invented butter packs when it is empty, and its sync button is enabled
    for them (`CartPanel.tsx:19-42`, `:70`, `:302`; BUG-006).
- **Risk:** fake results come back if a path is re-enabled, and they make the code harder to review.
- **Fix hint:** delete them, or keep one explicitly labeled fixture view behind a visible switch.

### CR-23 — Accessibility and display details

- **Page language:** the page declares `lang="en"` for a Ukrainian interface (`app/layout.tsx:12`,
  WCAG 3.1.1).
- **Buttons without actions:** microphone, "+", like, dislike, copy and the profile menu
  (`page.tsx:647-653`, `:739-745`, `:753-759`, `:917-919`; `PlannerResults.tsx:424-452`).
- **Cart dialogs:** they show every quantity in "шт", including weighed goods
  (`CartFlow.tsx:47-50`, `:108-109`), and the receipt lists product IDs instead of names
  (`CartFlow.tsx:104`).
- **FatSecret outcome:** it lists meal IDs instead of titles (`FatSecretFlow.tsx:106`).
- **Messages and labels:**
  - Every plan failure is titled "Помилка з'єднання з базою даних Сільпо" (`states.tsx:36`).
  - Calories are not rounded (`PlannerResults.tsx:852-856`).
  - The cart panel accepts `mode` but shows no data label (`CartPanel.tsx:68`).
- **Debug logs:** plan data is written to the browser console (`PlannerForm.tsx:500`, `:574-578`).

### CR-24 — Repository hygiene

- **Stray script:** `services/api/test_uliana_planner.py` is a manual script named like a test,
  sitting in the service root.
- **Unpinned SDK:** `google-genai` has no version bounds (`services/api/pyproject.toml:18`), although
  `agent/llm.py:57-72` relies on the newer `interactions` API. The package version is 0.1.0 while the
  API reports 0.2.0 (`app.py:29`).
- **Orchestrator readability:**
  - `agent/orchestrator.py:186-210` still says the context comes from "Rina DemoCatalog".
  - One-token-per-line formatting stretches the file to 1,837 lines.
  - The matching and optimization block is copied into four handlers.
- **Global caches:** the live catalog's caches are process-wide and never cleared
  (`catalog/live.py:111-112`), and `check_restrictions` reads details cached by any session
  (`:211-217`). Related to BUG-013.
- **Dead branch:** `fatsecret/export.py:311` can never return "failed", because `saved_meal_id` is
  always set there.

### CR-25 — Deployment images

- **Root user:** `deploy/api.Dockerfile` and `deploy/web.Dockerfile` run as root.
- **Development dependencies:** the web runtime copies the whole build folder, including the
  development dependencies in `node_modules` (`web.Dockerfile:20`); Next.js standalone output would
  be smaller.
- **Callback addresses:** `.env.example` points the callbacks at the API port
  (`http://localhost:8000/...`), while `deploy/docker-compose.yml:20-21` routes them through the web
  origin. Both work; the deployment runbook should say which to register.

## Checked and sound

- **Silpo OAuth state:** the MCP SDK compares it with `secrets.compare_digest`
  (`mcp/client/auth/oauth2.py:433` in the installed 2.x SDK); PKCE and client registration are left
  to the SDK.
- **FatSecret sign-in:**
  - the callback token is compared with `hmac.compare_digest` (`fatsecret/auth.py:77`);
  - user tokens are passed per call and never held globally (`fatsecret/client.py:77-82`).
- **Money:** integer kopiykas with `Decimal` rounding (`catalog/matching.py:24-34`,
  `mcp/adapters.py:350-360`).
- **Planner output:** the worker checks the request, totals and budget fields before storing a
  result (`routes/api.py:67-78`).
- **Live cart safeguards:** a fresh preview, a price and availability re-check, a cart snapshot
  comparison, idempotency keys, an in-flight guard and a read-back (`cart/service.py:162-362`), with
  the gaps in CR-01, CR-09 and CR-10.
- **FatSecret export:**
  - duplicate protection with a marker in the description;
  - read-back of every item;
  - a gate on Edamam-derived exports (`fatsecret/export.py:100-109`, `:253-336`).
- **Unknown labels and unverified products fail closed** (`meals/filters.py:114-123`,
  `catalog/matching.py:57-75`), except the keyword pass in CR-02.
- **Session isolation:** runs, previews and exports are kept per session (run 3).

## Not covered

- Live Silpo, Edamam and FatSecret calls, and any performance measurement.
- The quality of the test suites (only that they pass: 191 backend, 35 e2e, 33 UI in run 5).
- Generated contracts and fixture files line by line.
