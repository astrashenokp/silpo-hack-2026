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
