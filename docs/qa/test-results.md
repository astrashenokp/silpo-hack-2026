# QA test results

Actual observations, not intended behavior. Each run names its revision, environment and
data mode. Scenarios come from [QA and Demo](../QA_DEMO.md); defects are tracked in
[bugs](bugs.md).

## Run 1 — early intake, September 11, 2026

- **Revision:** `main` @ `0ef7fbb` ("feat(web): connect frontend planning flow"). Branch
  `feature/polina-integration-qa` adds only Polina's files on top of it.
- **Who:** Polina, with Claude Code.
- **Environment:** Windows 11 Pro; Python 3.13.14 virtual environment; Node 24.13.1 and
  npm 11.8.0; Next.js 16.3.4. Backend `uvicorn smart_basket.app:app` on `127.0.0.1:8000`
  with one worker; frontend production build (`npm run build`, `npm run start`) on `:3000`.
- **Mode:** `SMART_BASKET_MODE=demo`, `SMART_BASKET_MEALS_SOURCE=synthetic`, no provider
  credentials. Every response carried `X-Data-Mode: demo`. Nothing in this run is evidence of
  a live Silpo, Edamam or FatSecret path.

### Setup from a clean checkout

| Step | Command (repository root) | Result |
|---|---|---|
| Backend install, documented | `pip install -e 'services/api[test]'` | ❌ `pyproject.toml` parse error — BUG-001 |
| Backend install, workaround | dependencies from `pyproject.toml` installed by name; `PYTHONPATH=services/api/src` | ✅ |
| Dependency check | `pip check` | ✅ no broken requirements |
| Backend tests, documented | `pytest services/api/tests -q -p no:cacheprovider` | ❌ aborts on the same parse error — BUG-001 |
| Backend tests, neutral pytest config | `… -c <empty pytest.ini> --rootdir services/api` | ❌ collection error `GEMINI_API_KEY is not configured` — BUG-004 |
| Backend tests without the chat module | `… --ignore=services/api/tests/test_uliana_chat_flow.py` | ⚠️ 136 passed, 1 failed (`test_stale_cart_previews_block_changes[recalculate]`) — BUG-003 |
| Chat module with a dummy key | `GEMINI_API_KEY=dummy … test_uliana_chat_flow.py` | ❌ 5 passed, 5 failed — BUG-004 |
| Generated contracts | `services/api/scripts/export_contracts.py --check` | ✅ 22 contract and fixture files |
| Frontend install | `npm ci` in `apps/web` | ✅ |
| Frontend lint | `npm run lint` | ✅ 0 errors, 5 warnings (unused variables, `<img>`) |
| Frontend build | `npm run build` | ✅ |
| Start both services | Uvicorn, then `npm run start` | ✅ `GET /api/health` → `{"status":"ok","mode":"demo"}` on `:8000` and through `:3000` |

### Automated end-to-end suite (`tests/e2e`, 35 checks)

| Target | Result | Time |
|---|---|---|
| `http://127.0.0.1:8000` (API directly) | ✅ 34 passed, 1 xfailed (BUG-003) | 24 s |
| `http://localhost:3000` (through Next.js `/api` forwarding) | ✅ 34 passed, 1 xfailed (BUG-003) | 25 s |

### Acceptance scenarios

✅ passed · ❌ failed · ⚠️ partly · ⏸ not testable in this run (reason given)

| Scenario | Result | Evidence and notes |
|---|---|---|
| Valid form | ⚠️ | API keeps the request unchanged as `effectiveRequest`, money in integer kopiykas (e2e). The UI converts UAH once (`Math.round(budget * 100)`) but never sends the request — BUG-002 |
| Next.js / Python contract | ✅ API · ❌ UI | camelCase fields, integer money, nulls and enums through the proxy (e2e golden contract). The UI renders only fixtures — BUG-002 |
| Invalid/empty budget, days or people | ✅ API · ⚠️ UI | Server: 400 `VALIDATION_ERROR` for days 15 and 0, people 7, budget 0, USD, unknown label, cooking limit 3. UI validates budget and calories inline; days capped at 7 — BUG-007 |
| No login / expired session | ✅ API · ⏸ UI | 401 `AUTH_REQUIRED` without a session cookie. The UI recovery state exists only on the unused non-demo path — BUG-002 |
| Missing active cart context | ⏸ | Needs a live Silpo session |
| No purchase history | ✅ | Demo history is empty: `recurringItems: []`, meals still planned |
| Known recurrence | ⏸ | Demo history over HTTP is empty; Vika's unit tests pass |
| Shared vegetarian diet / excluded allergen | ⚠️ | API accepts and keeps `vegetarian`; the demo catalog checks only `peanut-free` (documented). The UI moves unsupported restrictions into notes — BUG-005 |
| Recipe scaled to 3 people | ✅ | 12 meals with 3 servings each; aggregates 600 g oats, 1440 g rice, 1200 g lentils; per-meal amounts add up to the aggregates |
| Package rounding | ✅ | Basket 49000 kopiykas as documented; rounding unit tests pass |
| Pet selected | ⏸ | Pets are kept in the request; pet demand is not implemented (documented limitation) |
| Very small budget | ✅ | `budgetMinor: 100` → `over_budget`, negative remaining, `canConfirmCart: false`, all 12 meals kept; cart preview refused with 409 |
| Unavailable product | ⏸ | Not reachable over HTTP in demo mode; matching unit tests pass |
| Include/remove restocking → recalculate | ❌ | Recalculation fails — BUG-003. The old cart preview is correctly invalidated (409) |
| Edamam/MCP timeout or rate limit | ⏸ | Needs live providers |
| Progress and failure | ✅ | Events report completed stages ending in `ready`; a failed worker ends as `failed` with an error envelope and polling stops |
| Existing cart has items | ✅ | Preview keeps the existing 3500 kopiykas separate: projected = existing + added |
| Repeated confirmation / uncertain timeout | ✅ · ⏸ | The same key returns the identical receipt; uncertain-timeout read-back needs a live cart |
| Price/cart changes after preview | ⚠️ | Unit tests pass for price, availability, cart and expiry changes; the recalculation variant fails — BUG-003 |
| Partial cart failure | ✅ | Per-item success and failure; failed items are not reported as added |
| Demo/live separation | ⚠️ | `X-Data-Mode: demo`, `dataMode: demo`, products labeled `synthetic`. The UI shows an unlabeled invented cart panel — BUG-006 |
| FatSecret personal-portion export | ✅ demo | One-person basis: exported `sourceQuantity` = meal amount ÷ servings |
| FatSecret account and app visibility | ⏸ | Needs consumer keys and the test account. Rina's handoff reports one manual success on September 11; not re-verified by Polina |
| FatSecret unknown match / stale preview | ✅ demo | `unmatched` → `canConfirm: false`; confirmation → 409 `UNRESOLVED_FOODS` |
| FatSecret repeated / partial export | ✅ demo | A repeat returns the same `exportId`; partial → `saved`, `failed`; failed meals have no `savedMealId` |
| FatSecret unavailable | ✅ demo | Every planning and cart check ran with FatSecret disconnected |
| Desktop, narrow screen and keyboard | ⏸ | Not checked in this run |
| Clean setup and hosted run | ❌ · ⏸ | Clean setup fails — BUG-001; no host yet |
| Extra: session isolation | ✅ | Another session gets 404 for runs, cart previews and exports |
| Extra: foreign browser origin | ✅ | POST with a foreign `Origin` → 403 `ORIGIN_NOT_ALLOWED`, directly and through Next.js |

### Deployment facts found during intake

- `API_BASE_URL` is read only by `next build` (BUG-008).
- POSTs from an origin missing in `SMART_BASKET_CORS_ORIGINS` are refused. Locally, opening
  `http://127.0.0.1:3000` makes every POST fail with 403 while `http://localhost:3000` works;
  the hosted origin must be listed exactly.
- On Windows, `http://localhost:8000` costs about 2.3 s per request (IPv6 is tried first and
  Uvicorn binds IPv4 only); `127.0.0.1` answers in about 0.3 s. Through Next.js both are fast.

### Not covered in this run

- Browser click-through of the UI: the headless browser tool did not start (lock timeout) and
  was dropped. UI findings come from code inspection of `0ef7fbb`.
- Live Silpo MCP/OAuth, Edamam and FatSecret: no credentials or authorized session were used.
- Responsive layout and keyboard operation.

### Intake package status

`docs/handoffs/integration-ready.md` is dated September 10 and names `sofiia-meal-planning` as
the active branch; the exact merged revision is not recorded yet (Rina, due September 11).
`docs/handoffs/alina.md`, `docs/handoffs/katia.md` and `docs/design/` do not exist yet.
Live-path evidence so far: Rina's FatSecret Saved Meal check (September 11); Arina's handoff
waits for an MCP token; Edamam is credential-gated (Sofiia).

## Run 2 — QA toolkit baseline, September 11, 2026

- **Revision:** `main` @ `0ef7fbb` with the QA toolkit from PR #19 (`feature/polina-qa-toolkit`).
  Same environment, stack and demo mode as run 1.
- **Purpose:** first run of every installed tool; see [the QA toolkit](tools.md) once #19 is merged.

| Tool | Result |
|---|---|
| Playwright 1.63.0, `desktop` and `mobile` (Pixel 7) | ✅ Smoke and keyboard specs pass on both. `api-wiring` fails as expected: no `POST /api/plans` within 10 s after "Скласти меню та кошик" — BUG-002 confirmed at runtime |
| axe-core 4.13.0, WCAG 2.1 AA | ❌ `color-contrast` (serious): account gate 5 nodes; planner form 16 nodes on desktop and 5 on mobile — BUG-009. No other serious or critical rule |
| Lighthouse 13.4.1 | Desktop: performance 100, accessibility 95, best practices 100, SEO 100. Mobile: 89, 95, 100, 100. Local production build, so indicative only |
| Schemathesis 4.26.1, 25 examples per operation | 13 of 18 operations (sign-in routes and Silpo search excluded), 328 cases, no server errors. Findings: 13 × 405 without `Allow` and 3 × schema-valid `X-Demo-Scenario` values rejected — BUG-010 |
| MCP Inspector 2.6.0 | Lists 24 tools of Playwright MCP and 29 of Chrome DevTools MCP |
| `probe_mcp.py` with python-sdk 2.2.0 | Lists 24 tools of a local Playwright MCP over Streamable HTTP. The Silpo MCP server was not contacted |

## Run 3 — UI flows, load, security review and submission rules, September 11, 2026

- **Revision:** `main` @ `d98b5f4` (after PRs #18 and #19), plus the new specs on branch
  `feature/polina-qa-round2`. Same environment and demo mode; the API runs with the local
  workaround for BUG-001.

### UI walk-through (Playwright, Desktop Chrome 1280×720 and Pixel 7)

| Flow | Observation |
|---|---|
| Account gate → guest → planner form | ✅ Works on both; no console errors; no horizontal overflow |
| Empty budget | ✅ Inline "Вкажіть бюджет."; no result |
| Golden input → result | ⚠️ Fixture plan (12 meals, 490 грн, 1 310 грн remaining) with the DEMO warnings. No request to `/api/*` during the whole session — BUG-002 |
| Greeting and time | ❌ A guest is greeted "Привіт, Катерино!"; timestamps are a fixed "10:39" — BUG-006 |
| Regular purchases and ingredient prices | ❌ Butter and Jameson whiskey, each twice, for a guest without history; ingredient rows show those prices and photos — BUG-011 |
| "Додати все в кошик Сільпо" | ❌ Fills the cart panel at once, without a preview — BUG-012 |
| "Синхронізувати з Сільпо" | ❌ Preview opens but is already stale; "Підтвердити додавання" stays disabled — BUG-012 |
| "↻ Перерахувати кошик" | ⚠️ Replays scripted steps and resets the cart panel to the invented butter packs |
| FatSecret save | ✅ Demo: preview with "1 особиста порція на страву" and "не щоденниковий запис", confirmation, per-meal outcome |
| Cart controls on narrow screens | ✅ Reachable on Pixel 7, 1024, 1279 and 1280 px |

`tests/ui/specs/flows.spec.ts` on both projects: 14 passed — 6 real checks and 8 expected
failures that reproduce BUG-006, BUG-011 and BUG-012.

### Load and isolation (API directly, 30 parallel demo sessions)

30 of 30 plans completed; from `POST /api/plans` to the terminal state p50 0.23 s and max 0.24 s.
No session could read another session's run (30 of 30 answered 404). 300 cookie-less
`GET /api/context` requests created 300 server-side sessions in 0.6 s; none expire — BUG-013.

### Security review (read-only)

Sound: per-session isolation, the POST origin allowlist, an `HttpOnly` + `SameSite=Lax` session
cookie, the FatSecret callback token check with `hmac.compare_digest`, no tokens in status
responses, generic 500 messages. Findings for a public deployment: unbounded sessions and runs, no
rate limit, no `Secure` cookie flag, public `/docs` — BUG-013. The Silpo OAuth state and PKCE
checks are delegated to the MCP SDK and were not re-verified.

### Submission rules

Read from the official site and rules on September 11: video pitch 3–5 minutes, submission
through the registration form by September 14, 23:59 Kyiv time, the Silpo MCP as a functionally
significant component, a list of third-party objects, a generative-AI disclosure and 90 days of
access for the organizer. Details and the risks they create: [submission checklist](submission.md);
the recording plan: [demo script](demo-script.md).

## Run 4 — retest after PRs #20–#22, September 11, 2026

- **Revision:** `main` @ `333d037` (Rina's #20 syntax fix, #21 cart adapter and #22 live catalog
  and cart flow; Alina's shared cart `1a121e0`) merged into `feature/polina-qa-round2`. Demo
  mode; the frontend was rebuilt.

| Check | Result |
|---|---|
| Documented install `pip install -e 'services/api[test]'` | ✅ Works — BUG-001 fixed |
| Documented backend tests | ❌ Collection still stops on `GEMINI_API_KEY` — BUG-004 |
| Backend tests without the chat module | ✅ 148 passed, including the recalculation variant that failed before — BUG-003 fixed |
| Chat module with a dummy key | ❌ 7 passed, 3 failed (stale 34000 and "1460.00 UAH" expectations) — BUG-004 |
| Generated contracts | ❌ `packages/contracts/openapi.json` is stale — BUG-014 (new) |
| e2e through Next.js, BUG-003 `xfail` removed | ✅ 35 of 35 |
| UI specs on desktop and Pixel 7 | ✅ 27 passed, 1 skipped; expected failures reproduce BUG-002, BUG-006, BUG-011, BUG-012, BUG-015 (mobile) and BUG-016 |
| Cart panel by window width | ❌ Absent at 768, 1024 and 1279 px, present at 1280 and 1440 px — BUG-015 (new) |
| Over-budget plan (budget 100) | ⚠️ "Бюджет перевищено на 390,00 грн." is shown, but "Додати все в кошик Сільпо" stays enabled and the preview opens — BUG-016 (new) |
| CI on PR #23 before these updates | Images ✅ (the API image builds again), frontend ✅; backend ❌ BUG-004; e2e ❌ only the strict XPASS of the fixed BUG-003; UI ❌ one timeout caused by BUG-015 |
| `deploy/run-local.ps1` | ✅ Cold start with captured output, restart with only the web app down, `-Test`, `-Stop` |

The live Silpo checks that Arina and Rina reported on September 11 (OAuth, 40 tools, ready cart
context, live product search, a reviewed cart write with read-back awaiting one authorized
real-cart check) were not repeated by Polina, and the UI does not use these paths yet (BUG-002).

## Run 5 — UI connected to the API, September 11, 2026

- **Revision:** `afe586e`, that is PR #27 (the web UI connected to the Python API) with `main` @
  `acac9d3` (Uliana's #26) merged in; merged into `main` as `cf7ebbf`. Demo mode, guest session;
  the frontend was rebuilt.

| Check | Result |
|---|---|
| Documented backend tests without `GEMINI_API_KEY` | ✅ 191 passed — BUG-004 fixed |
| Generated contracts (`export_contracts.py --check`) | ✅ 22 files current — BUG-014 fixed |
| e2e through Next.js | ✅ 35 of 35 |
| UI specs against the running API, desktop and Pixel 7 | ✅ 33 passed, 1 skipped (cart confirmation on mobile, BUG-015); the 9 expected failures reproduce BUG-006, BUG-011, BUG-012 (adding without a preview), BUG-015 (mobile) and BUG-016 |
| Plan from the form | ✅ `POST /api/plans`, then polling; the result shows the API's `dataMode` — BUG-002 fixed |
| "↻ Перерахувати кошик" | ✅ the server's next version appears as a second plan |
| Cart preview and confirmation | ✅ the preview comes from `/api/cart/preview`, and "Підтвердити додавання" ends in "Результат синхронізації". "Додати все" still skips the preview — BUG-012 partly fixed |
| FatSecret save | ✅ preview of one personal portion, confirmation and export outcome through the API |
| Silpo and FatSecret connect buttons | ✅ with the provider responses mocked: Silpo goes through `/api/auth/silpo/start` and back to the app with the status read; a FatSecret start error is explained on the page. Real sign-in not run: it needs the demo accounts |
| Over-budget plan (budget 100) | ❌ "Бюджет перевищено на 110,00 грн.", yet "Додати все" stays enabled. "Синхронізувати з Сільпо" gets 409 `STALE_PLAN` from `/api/cart/preview`, and the page shows "Помилка синхронізації кошика Сільпо" with the API's English message and a retry that cannot succeed — BUG-016 |
| Result screen of that plan | ⚠️ the cart panel lists the API's three demo products (210,00 грн), but ingredient rows keep the invented butter and whiskey prices and images (BUG-011) and the panel the invented store address (BUG-006) |
| CI on PR #27 (`afe586e`) | ✅ all five jobs: backend, frontend, e2e, images, UI |
| CI on `main` after the merge (`cf7ebbf`) | ✅ all five jobs |

## Run 6 — full UI-API connection, September 12, 2026

- **Revision:** `feature/connect-ui-to-api` (from `main` @ `cf7ebbf`, PR #31): the result screen
  renders `MealPlan`, `ProposedBasket`, `BudgetSummary` and `RecurringSuggestions` instead of the
  fixed cards; a new `POST /api/chat` route; the allergen/preference fields read `GET /api/filters`.
  Not merged; demo mode, guest session.

| Check | Result |
|---|---|
| Backend tests without `GEMINI_API_KEY` | ✅ 191 passed |
| Generated contracts (`export_contracts.py --check`) | ✅ current |
| e2e through Next.js | ✅ 40 of 40 (5 new: chat requires a session, rejects an empty message, answers in the contract shape, reports a missing interpreter instead of crashing, a reply without a new plan keeps the current plan confirmable) |
| UI specs against the running API, desktop and Pixel 7 | ✅ 38 of 38. No `test.fail` markers remain in `flows.spec.ts` |
| Result screen | ✅ every requested day, the chosen products with source and restriction badges, substitutions, unresolved requirements and the real recurring suggestions from `recurringItems` — no invented butter, whiskey, name or store address (BUG-006, BUG-011 fixed) |
| Recurring purchases | ⚠️ shown from the API, but selecting one is disabled with a stated reason: the API cannot match a recurring item to a product yet (CR-04, unfixed) |
| "Додати все в кошик Сільпо" | ✅ opens the API preview immediately, no local fill-in step (BUG-012 fixed) |
| Cart panel at 768, 1024, 1279, 1280 and 1440 px | ✅ reachable at every width: below `xl` it renders inline instead of in the side column (BUG-015 fixed) |
| Over-budget plan (budget 100) | ✅ "Додати все" is disabled with the existing budget warning as the reason; no failed sync attempt (BUG-016 fixed) |
| Allergen/preference fields | ✅ load from `GET /api/filters` and offer only those labels; a selection reaches `restrictions`/`preferences` instead of `notes` (BUG-005 fixed) |
| Chat message ("зроби дешевше") | ✅ reaches `/api/chat`; without `GEMINI_API_KEY` (CI and this run) the reply names the missing key instead of a silent no-op |
| CI on PR #31 | ✅ all five jobs, on both commits (the connection and the recurring-selection guard) |

Not covered: a signed-in Silpo or FatSecret run from the UI, a chat message with a real Gemini
key, and CR-04 (recurring purchases still cannot be matched to products by the API).

