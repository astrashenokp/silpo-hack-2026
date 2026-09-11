# Handoff: Polina — final integration, QA and release (draft)

Working document. Final values are filled in by September 13; the recording and
submission status on September 14.

- **Delivery date:** in progress. Early intake September 11; release target September 13;
  recording and submission September 14.
- **PR / commit:** intake of `main` @ `0ef7fbb` (PR #18), QA toolkit (PR #19), round 2 on
  branch `feature/polina-qa-round2`.
- **Receiving teammates:** the whole team.
- **Completed so far:** runs 1–3 (setup, backend and frontend checks, HTTP scenarios, UI
  walk-through, load and security review); end-to-end suite; QA toolkit; CI workflow;
  deployment draft and local launcher; demo script; submission checklist; bug list with owners.
- **Main files:** `tests/`, `docs/qa/` (test results, bugs, tools, demo script, submission
  checklist), `deploy/` (runbook, Docker, `run-local.ps1`), `.github/workflows/ci.yml`.
- **Checks and results:** [test results](../qa/test-results.md).
- **Known issues:** [bug list](../qa/bugs.md). BUG-001 and BUG-003 are fixed and retested.
  Open blocker: BUG-002 (UI not connected to the API); for the video also BUG-011, BUG-012
  and BUG-015.

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
| Planning pipeline over HTTP (Uliana, Sofiia, Rina, Vika) | demo, working | End-to-end suite, runs 1 and 4 (35 of 35 in run 4) |
| Recalculation | working in demo | Fixed in #22; retested in run 4 |
| Web UI → Python API | not connected | BUG-002 |
| Silpo OAuth, tools, context and product search | live, reported by Arina and Rina on September 11; not re-verified by Polina | `docs/handoffs/arina.md`, `docs/handoffs/rina.md` |
| Silpo cart writes | live service with preview, revalidation, idempotency and read-back; one authorized real-cart check still open | Rina's handoff |
| Edamam | not verified | Credential-gated (Sofiia) |
| FatSecret export | demo verified; live reported by Rina on September 11, not re-verified | Needs consumer keys and the test account |

## Release checklist ([QA and Demo](../QA_DEMO.md#september-1213-polinas-release-checklist))

- [ ] Reproduce setup from the delivered revision — blocked by BUG-001; workaround works
- [ ] Connect frontend, HTTP API, agent and provider adapters — UI not connected (BUG-002); providers not live
- [x] Start Next.js and Python; `/api` forwarding and background plan execution work locally
- [ ] OAuth redirect/session behavior and CORS on the hosted origin
- [ ] Acceptance scenarios run, bugs assigned and retested — run 1 recorded; owners to be notified; retest pending
- [ ] A real MCP interaction and the Edamam path verified
- [ ] FatSecret export acceptance checks on the live account
- [ ] No blocking defects in the demo flow — two blockers open
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
