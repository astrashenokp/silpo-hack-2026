# Handoff: Polina — final integration, QA and release (draft)

Working document. Final values are filled in by September 13; the recording and
submission status on September 14.

- **Delivery date:** in progress. Early intake September 11; release target September 13;
  recording and submission September 14.
- **PR / commit:** intake of `main` @ `0ef7fbb` (PR #18), QA toolkit (PR #19), round 2 (PR #23),
  UI connected to the API (PR #27), run 5 records on branch `feature/polina-qa-run5`.
- **Receiving teammates:** the whole team.
- **Completed so far:** runs 1–5 (setup, backend and frontend checks, HTTP scenarios, UI
  walk-through, load and security review, retests); end-to-end suite; QA toolkit; CI workflow;
  deployment draft and local launcher; demo script; submission checklist; bug list with owners;
  the web UI wired to the Python API (plans, recalculation, cart, FatSecret, sign-in routes).
- **Main files:** `tests/`, `docs/qa/` (test results, bugs, tools, demo script, submission
  checklist), `deploy/` (runbook, Docker, `run-local.ps1`), `.github/workflows/ci.yml`.
- **Checks and results:** [test results](../qa/test-results.md).
- **Known issues:** [bug list](../qa/bugs.md). BUG-001–BUG-006, BUG-011, BUG-012, BUG-014,
  BUG-015 and BUG-016 are fixed and retested. Open, none blocking the demo: days capped at 7
  (BUG-007), `API_BASE_URL` build-time only (BUG-008), text contrast (BUG-009), contract
  detail (BUG-010), public-deployment hardening (BUG-013).

## Launch the local demo today (PowerShell, repository root)

One command installs what is missing, works around BUG-001 without changing any file, starts
both services and, with `-Test`, runs the e2e and UI suites:

```powershell
powershell -ExecutionPolicy Bypass -File deploy/run-local.ps1 -Test
powershell -ExecutionPolicy Bypass -File deploy/run-local.ps1 -Stop
```

Manual alternative (the documented install works again since #20):

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
expected 35 passed. Rebuild the frontend after pulling changes to `apps/web`.

## Recovery

- After an API restart all sessions, plans and receipts are gone: reload the page and create
  the plan again; reconnect FatSecret.
- Every POST fails with 403 `ORIGIN_NOT_ALLOWED`: open the origin listed in
  `SMART_BASKET_CORS_ORIGINS` (locally `http://localhost:3000`).
- API address changed: rebuild the frontend; `API_BASE_URL` is baked in at build time.
- Hosting: see [deployment runbook](../../deploy/README.md).

## Live versus mock, as verified by Polina

| Path | Status | Evidence |
|---|---|---|
| Planning pipeline over HTTP (Uliana, Sofiia, Rina, Vika) | demo, working | End-to-end suite, runs 1, 4 and 5 (35 of 35) |
| Recalculation | working in demo, from the UI too | Fixed in #22; the UI calls it since #27; run 5 |
| Web UI → Python API | connected (PR #27): plans, recalculation, cart, FatSecret, sign-in routes | Run 5, UI specs against the running API; the chat has no API endpoint |
| Silpo OAuth, tools, context and product search | live, reported by Arina and Rina on September 11; not re-verified by Polina | `docs/handoffs/arina.md`, `docs/handoffs/rina.md` |
| Silpo cart writes | live service with preview, revalidation, idempotency and read-back; one authorized real-cart check still open | Rina's handoff |
| Edamam | not verified | Credential-gated (Sofiia) |
| FatSecret export | demo verified; live reported by Rina on September 11, not re-verified | Needs consumer keys and the test account |

## Release checklist ([QA and Demo](../QA_DEMO.md#september-1213-polinas-release-checklist))

- [ ] Reproduce setup from the delivered revision — the documented install works since #20 (run 4); repeat on the frozen revision
- [ ] Connect frontend, HTTP API, agent and provider adapters — UI connected to the API in #27 (run 5); providers not yet run live from the UI
- [x] Start Next.js and Python; `/api` forwarding and background plan execution work locally
- [ ] OAuth redirect/session behavior and CORS on the hosted origin
- [ ] Acceptance scenarios run, bugs assigned and retested — runs 1–5 recorded; owners to be notified
- [ ] A real MCP interaction and the Edamam path verified
- [ ] FatSecret export acceptance checks on the live account
- [ ] No blocking defects in the demo flow — no blocker or High defect open since #31; only Low/Medium polish items remain
- [ ] Demo account, cart context and a repeatable starting state
- [ ] Revision frozen on September 13 with deploy URL, launch and recovery steps
- [ ] Clearly labeled synthetic backup
- [ ] Current submission rules: links, video access, duration and format

## Demo plan (draft)

Timed script, what to say and not to say, the pre-recording checklist and recovery:
[demo script](../qa/demo-script.md). Golden input: 3 people, 4 days, UAH 1,800, 2,000 kcal per
person per day, shared vegetarian meals, 1 cat, recurring analysis on. Backup: the same flow in
demo mode with the DEMO label visible, never presented as a live run.

## To decide or fill in

| Item | Owner | Status |
|---|---|---|
| Hosting option | Polina | Pending, see the deployment runbook |
| Deploy URL | Polina | — |
| Frozen revision | Polina | September 13 |
| Presenter | Team | — |
| Submission-account owner | Team | — |
| Portal requirements | Polina | Read on September 11: [submission checklist](../qa/submission.md); re-check on the 12th and 14th |
| Recording and backup links | Polina | September 14 |

## Receiving teammate's verification

Pending.
