# Handoff: Polina — final integration, QA and release (draft)

Working document. Final values are filled in by September 13; the recording and
submission status on September 14.

- **Delivery date:** in progress. Early intake September 11; release target September 13;
  recording and submission September 14.
- **PR / commit:** branch `feature/polina-integration-qa`, intake of `main` @ `0ef7fbb`.
- **Receiving teammates:** the whole team.
- **Completed so far:** intake run 1 (setup, backend and frontend checks, HTTP scenarios);
  automated end-to-end suite; CI workflow; deployment draft; bug list with owners.
- **Main files:** `tests/e2e/`, `docs/qa/test-results.md`, `docs/qa/bugs.md`, `deploy/`,
  `.github/workflows/ci.yml`.
- **Checks and results:** [test results](../qa/test-results.md).
- **Known issues:** [bug list](../qa/bugs.md). Open blockers: BUG-001 (clean setup) and
  BUG-002 (UI not connected to the API).

## Launch the local demo today (PowerShell, repository root)

The documented install fails until BUG-001 is fixed. Workaround:

```powershell
python -m venv services/api/.venv
& services/api/.venv/Scripts/python.exe -m pip install "fastapi>=0.115,<1" "uvicorn>=0.34,<1" "pydantic>=2.11,<3" "mcp>=2.2,<3" "httpx2>=2.12,<3" google-genai "pytest>=8,<10" "httpx>=0.28,<1" "pytest-asyncio>=0.23.0"
$env:PYTHONPATH = 'services/api/src'
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
expected 34 passed, 1 xfailed. After BUG-001 is fixed, follow `services/api/README.md`.

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
| Planning pipeline over HTTP (Uliana, Sofiia, Rina, Vika) | demo, working | End-to-end suite, run 1 |
| Recalculation | failing | BUG-003 |
| Web UI → Python API | not connected | BUG-002 |
| Silpo OAuth and MCP | not verified by Polina | Needs the authorized demo account |
| Edamam | not verified | Credential-gated (Sofiia) |
| FatSecret export | demo verified; live reported by Rina on September 11, not re-verified | Needs consumer keys and the test account |
| Silpo cart writes | demo only | Needs a live Silpo session and cart context |

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

Golden input: 3 people, 4 days, UAH 1,800, 2,000 kcal per person per day, shared vegetarian
meals, 1 cat, recurring analysis on. Story as in
[QA and Demo](../QA_DEMO.md#september-14-recording-and-submission). Backup: the same flow in
demo mode with the DEMO label visible, never presented as a live run.

## To decide or fill in

| Item | Owner | Status |
|---|---|---|
| Hosting option | Polina | Pending, see the deployment runbook |
| Deploy URL | Polina | — |
| Frozen revision | Polina | September 13 |
| Presenter | Team | — |
| Submission-account owner | Team | — |
| Portal requirements (format, duration, fields) | Polina | Check on September 12 at https://ai-factory.silpo.ua/ |
| Recording and backup links | Polina | September 14 |

## Receiving teammate's verification

Pending.
