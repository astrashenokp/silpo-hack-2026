# Bug list

Final-integration defects found by Polina. Each author fixes her own module
([decision owners](../WORKFLOW.md#decision-owners)); Polina retests and updates the
status here. Results of each run are in [test results](test-results.md).

Severity: **Blocker** stops setup or the demo flow; **High** breaks a required
feature; **Medium** misleads the user or a reviewer; **Low** is cosmetic or
documentation.

Revision under test: `main` @ `0ef7fbb` (September 11, 2026). This list has not yet
been sent to the owners; Polina shares it with the team.

| ID | Severity | Summary | Owner | Status |
|---|---|---|---|---|
| BUG-001 | Blocker | Backend cannot be installed or tested from a clean checkout (`pyproject.toml` syntax error) | Rina (file owner); introduced by merge `f7b10e0` from Uliana's branch | Open |
| BUG-002 | Blocker | Web UI never calls the Python API: plan, cart and FatSecret are simulated in the browser | Ksiusha + Alina | Open |
| BUG-003 | High | "Recalculate basket" always fails with `PLANNER_FAILED` and leaves no confirmable plan | Uliana | Open |
| BUG-004 | High | Chat tests abort the backend suite without `GEMINI_API_KEY`; with a key 5 of 10 fail | Uliana | Open |
| BUG-005 | High | Unsupported dietary restrictions typed in the form are silently moved into `notes` | Ksiusha | Open |
| BUG-006 | Medium | Invented, unlabeled cart panel, store address and user name in the UI | Alina + Ksiusha | Open |
| BUG-007 | Low | Days counter stops at 7; the contract allows 1–14 | Ksiusha (confirm with Katia) | Open |
| BUG-008 | Low | `API_BASE_URL` is documented as runtime configuration but only applies at `next build` | Ksiusha | Open |

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
- **Expected:** the suite runs and passes without secrets, with Gemini mocked or injected.
- **Impact:** CI stays red and the handoffs' test counts cannot be reproduced.

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
  Becomes live as soon as BUG-002 is fixed.

## BUG-006 — Invented, unlabeled data in the UI

- **Where:** `apps/web/src/app/page.tsx:532-585` (`SetupCartPreview`: two
  "Масло солодковершкове Галичина" items at 124.00/79.99 ₴, a discount total and the store
  "просп. Бандери, 23 (Самовивіз)"); `page.tsx:405` and `:662` greet "Катерина"/"Катерино"
  after the simulated connection.
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
