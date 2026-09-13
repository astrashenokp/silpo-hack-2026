# Handoff: Polina — final integration, QA and release

- **Deploy URL:** https://p01--web--2n7f5yvrbnqy.code.run — Northflank Cloud, Europe-West
  (London). Set up by Polina, live-verified end to end September 12–13: `POST /api/plans` runs a
  full plan to `completed` with real meals and products; e2e 40/40 and the full Playwright UI
  suite 42/42 both pass against this exact public URL, not just locally.
- **Frozen revision:** `main` @ `402bdcb`, deployed and confirmed running. CI green (5/5).
  Verified against the live URL at this revision on September 13: e2e 40/40 and the full
  Playwright UI suite 42/42 (desktop + Pixel 7). Northflank redeploys `web` automatically on a
  push to `main` — both September 13 fixes reached the live site without a manual rebuild.
- **Delivery date:** hosting decided and live September 12–13 (treated as the deadline day);
  recording and submission still ahead.
- **PR / commit:** intake (#18), QA toolkit (#19), round 2 (#23), whole-project code review
  (#29), UI fully connected to the API (#27, #31), QA runs 5–14 (#28, #32, #33, #34, #36, #37,
  #38, #39).
- **Receiving teammates:** the whole team.
- **Completed so far:** runs 1–14 (setup, backend and frontend checks, HTTP scenarios, UI
  walk-through, load and security review, full toolkit sweeps, live-credential verification, a
  real Docker Compose rehearsal, the live public deployment, and two browser-agent batteries
  against it); end-to-end suite; QA toolkit; CI workflow; deployment runbook
  and local launcher; demo script; submission checklist; bug list with owners; whole-repository
  code review; the web UI fully wired to the Python API, including chat.
- **Main files:** `tests/`, `docs/qa/` (test results, bugs, tools, demo script, submission
  checklist, code review), `deploy/` (runbook, Docker, `run-local.ps1`), `.github/workflows/ci.yml`.
- **Checks and results:** [test results](../qa/test-results.md).
- **Known issues:** [bug list](../qa/bugs.md). BUG-001–BUG-006, BUG-011, BUG-012, BUG-014,
  BUG-015, BUG-016, BUG-018 and BUG-020 are fixed and retested. Open, none blocking the demo:
  days capped at 7 (BUG-007), `API_BASE_URL` build-time only (BUG-008), text contrast
  (BUG-009), contract detail (BUG-010, extended in run 7), public-deployment hardening
  (BUG-013), a FatSecret route-shadowing 404/405 mismatch (BUG-017, found in run 7), no live
  `GEMINI_API_KEY` so chat cannot be demoed (BUG-019, needs a key from Uliana), and nine of the
  ten dietary restrictions emptying the basket on the demo data path (BUG-021, Rina). The one
  open High-severity item from the code review, CR-04 (recurring purchases cannot be matched to
  products by the API), is deliberately unfixed pending Rina/Vika/Uliana.
- **Two things to say out loud before recording:** pick no dietary restriction or only
  `peanut-free` (BUG-021), and do not script live chat (BUG-019).

## Launch the local demo today (PowerShell, repository root)

One command starts both services and, with `-Test`, runs the e2e and UI suites:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/run-local.ps1 -Test
powershell -ExecutionPolicy Bypass -File deploy/run-local.ps1 -Stop
```

Manual alternative:

```powershell
python -m venv services/api/.venv
& services/api/.venv/Scripts/python.exe -m pip install -e 'services/api[test]'
& services/api/.venv/Scripts/python.exe -m uvicorn smart_basket.app:app --host 127.0.0.1 --port 8000
```

Second terminal:

```powershell
cd apps/web
npm.cmd ci
npm.cmd run build
npm.cmd run start
```

Open `http://localhost:3000` (not `127.0.0.1`: every POST would get 403). Check the stack
from a third terminal with `& services/api/.venv/Scripts/python.exe -m pytest tests/e2e`:
expected 40 passed. Rebuild the frontend after pulling changes to `apps/web`.

## Recovery

- After an API restart all sessions, plans and receipts are gone: reload the page and create
  the plan again; reconnect FatSecret.
- Every POST fails with 403 `ORIGIN_NOT_ALLOWED`: open the origin listed in
  `SMART_BASKET_CORS_ORIGINS` (locally `http://localhost:3000`).
- API address changed: rebuild the frontend; `API_BASE_URL` is baked in at build time. On
  Northflank this means triggering a real **Rebuild** of the `web` service, not just a redeploy —
  a redeploy reuses the old image and keeps the stale address (hit this exact issue setting up
  the live deploy; `getaddrinfo ENOTFOUND api` in the runtime logs is the symptom).
- Hosting: see [deployment runbook](../../deploy/README.md). Live now on Northflank — see the
  deploy URL above. If the API service restarts and its origin/callback env vars are ever lost,
  every POST fails with 403 until `SMART_BASKET_CORS_ORIGINS`, `SMART_BASKET_FRONTEND_URL`,
  `SILPO_OAUTH_CALLBACK_URL` and `FATSECRET_OAUTH_CALLBACK_URL` are restored to the `web`
  service's exact public URL.

## Live versus mock, as verified by Polina

| Path | Status | Evidence |
|---|---|---|
| Planning pipeline over HTTP (Uliana, Sofiia, Rina, Vika) | demo, working | End-to-end suite, every run through run 14 (40 of 40), including against the live public URL |
| Recalculation | working in demo, from the UI too | Fixed in #22; the UI calls it since #27; runs 5–14 |
| Web UI → Python API | fully connected (PR #27, completed in #31): plans, recalculation, cart, FatSecret, sign-in routes, chat (`POST /api/chat`) | Runs 5–14, UI specs against the running API, now 42/42 desktop + Pixel 7, including against a real Docker deployment and the live public URL |
| Silpo OAuth, tools, context and product search | live and independently re-verified by Polina, not only self-reported | Run 9–10: `claude mcp login silpo` and the MCP Inspector both connected a real account; 40 live tools (matches Arina's and Rina's Sep 11 count), still authenticated a full day later without a new sign-in; all 12 tool names the backend code calls exist verbatim on the live server; real profile, food-restriction, family/pet, cart and product-search responses each matched the exact shape the adapter code expects, including the `displayRatio`-based package-size parsing from Rina's #30. **Not yet exercised: the same login through our own product's `/api/auth/silpo/start`** (only the raw MCP tools were driven directly, not our app's OAuth client), and the cart-write tool (`silpo_add_or_update_cart_products`, intentionally not attempted — it would modify a real cart) |
| Silpo cart writes | live service with preview, revalidation, idempotency and read-back; one authorized real-cart check still open | Rina's handoff |
| Edamam | not verified | Credential-gated (Sofiia) |
| FatSecret export | demo verified; live saved-meal write reported by Rina on September 11, not re-verified; consumer credentials verified live by Polina (`request_token` succeeded, two-legged `foods.search` returned real data, `foods.search.v5` is unavailable for this app's scope) | Run 8; the full three-legged write still needs a human to authorize a FatSecret account in a browser |

## Release checklist ([QA and Demo](../QA_DEMO.md#september-1213-polinas-release-checklist))

- [x] Reproduce setup from the delivered revision — the documented install works since #20; reproduced again on every run through run 14, including inside the Docker rehearsal
- [x] Connect frontend, HTTP API, agent and provider adapters — fully connected in #27/#31; the live Silpo *adapter* code itself is verified against real data (run 9), but not yet driven through our own app's sign-in button
- [x] Start Next.js and Python; `/api` forwarding and background plan execution work locally
- [x] OAuth redirect/session behavior and CORS on the hosted origin — **live on Northflank now**: `POST /api/plans` reaches `completed` on the real public URL with the correct origin, and e2e (40/40) plus the full UI suite (42/42) both pass against it, not only locally. Silpo/FatSecret OAuth callbacks are pointed at this origin in the API's env vars but not yet clicked through live on this exact deploy
- [x] Acceptance scenarios run, bugs assigned and retested — runs 1–14 recorded; every author-owned bug found has a named owner in `docs/qa/bugs.md`
- [x] A real MCP interaction verified — live Silpo OAuth, 40 tools and real profile/cart/product-search calls, runs 9–10; Edamam still credential-gated (Sofiia)
- [ ] FatSecret export acceptance checks on the live account — consumer credentials verified live (run 8) and now configured on the hosted API too; the full user-authorized write still needs a human login
- [x] No blocking defects in the demo flow — no blocker or High defect open since #31 in Polina-tested paths; CR-04 is the one open High finding, deliberately left to its owners
- [ ] Demo account, cart context and a repeatable starting state — a live Silpo account is now available (used in runs 9–10) but its cart is a real teammate's cart, not a rehearsal-safe demo one; need a dedicated demo account or an agreed reset step before recording
- [x] Revision frozen with deploy URL, launch and recovery steps — `main` @ `402bdcb`, live at the deploy URL above, launch/recovery documented
- [x] Clearly labeled synthetic backup — `DemoBadge`, `X-Data-Mode`, the DEMO warning text; verified in every UI run
- [x] Current submission rules: links, video access, duration and format — read September 11, [submission checklist](../qa/submission.md); re-check before the 14th, since the portal FAQ did not load on the 11th

## Demo plan (draft)

Timed script, what to say and not to say, the pre-recording checklist and recovery:
[demo script](../qa/demo-script.md). Golden input: 3 people, 4 days, UAH 1,800, 2,000 kcal per
person per day, shared vegetarian meals, 1 cat, recurring analysis on. Backup: the same flow in
demo mode with the DEMO label visible, never presented as a live run.

## To decide or fill in

| Item | Owner | Status |
|---|---|---|
| Hosting option | Polina | **Done** — Northflank Cloud, two services (`api`, `web`) built from `deploy/api.Dockerfile` and `deploy/web.Dockerfile` |
| Deploy URL | Polina | https://p01--web--2n7f5yvrbnqy.code.run — live-verified (e2e 40/40, UI 42/42); redeploys automatically on a push to `main` |
| Frozen revision | Polina | `main` @ `402bdcb`, deployed, CI green (5/5), live-verified e2e 40/40 + UI 42/42 |
| Presenter | Team | — |
| Submission-account owner | Team | — |
| Portal requirements | Polina | Read on September 11: [submission checklist](../qa/submission.md); re-check on the 12th and 14th |
| Demo Silpo account | Team | A live account is now connected (runs 9–10), but it is a teammate's real account with a real cart — decide whether to use it as-is (clearing rehearsal additions first) or set up a dedicated demo account before recording |
| Recording and backup links | Polina | September 14 |

## Receiving teammate's verification

Pending.
