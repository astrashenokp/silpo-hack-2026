# End-to-end checks

Black-box checks of a running stack over its public HTTP surface. They cover the
[QA and Demo](../../docs/QA_DEMO.md) scenarios that demo mode can exercise, and they
mark known defects as `xfail` with the ID from [the bug list](../../docs/qa/bugs.md)
(`xfail_strict` makes a fixed bug fail loudly until its marker is removed). Owner:
Polina. They complement, not replace, the module tests in `services/api/tests`.

## Run locally (PowerShell, repository root)

1. Start the backend and the frontend as described in the
   [backend guide](../../services/api/README.md): Uvicorn on `127.0.0.1:8000`, then
   `npm.cmd run build` and `npm.cmd run start` (or `npm.cmd run dev`) in `apps/web`.
2. In a third terminal:

   ```powershell
   & services/api/.venv/Scripts/python.exe -m pip install -r tests/e2e/requirements.txt
   & services/api/.venv/Scripts/python.exe -m pytest tests/e2e
   ```

`E2E_BASE_URL` selects the target:

| Value | Use |
|---|---|
| `http://localhost:3000` (default) | Through Next.js `/api` forwarding, as the browser sees it |
| `http://127.0.0.1:8000` | The Python API directly, to separate backend from forwarding problems |
| Deployed web origin | Post-deploy smoke check of the hosted demo |

On Windows use `127.0.0.1`, not `localhost`, for the direct API: Uvicorn listens on
IPv4 only and every `localhost` request first waits about 2 s for IPv6.
`E2E_POLL_TIMEOUT_SECONDS` (default 30) bounds plan and export polling.

## Coverage

| File | Scenarios |
|---|---|
| `test_golden_flow.py` | Health/mode label, filter labels, session cookie, progress stages, golden plan contract (fields, slots, servings, integer money, line/basket/remaining totals, synthetic labels), documented demo numbers, per-meal vs aggregate ingredients, 25/35/40 calorie split, cart preview → confirm → idempotent repeat, FatSecret one-person portion → export → idempotent repeat |
| `test_failure_states.py` | No session, invalid inputs, unknown demo scenario, unknown run, foreign browser origin, cross-session isolation (runs, cart, exports), worker failure, very small budget and cart gate, stale version, partial/failed cart receipts, recalculation (unknown IDs, preview invalidation, new version), FatSecret unmatched/partial/failed exports |

Not covered here: browser UI behaviour (manual checks in `docs/qa/test-results.md`)
and live Silpo MCP, Edamam or FatSecret accounts, which need credentials and an
authorized session.
