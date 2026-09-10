# Smart Basket API — Rina's demo implementation

Python 3.12+; verified on Windows with Python 3.14.6. FastAPI + Pydantic + Uvicorn.
The default run is synthetic. No Silpo, Edamam or FatSecret credentials are needed
for the local demo, but Sofiia's Edamam adapter boundary and setting names are in
place for the live access check.
Use one Uvicorn worker: sessions, runs and operation receipts are stored in memory
and disappear on restart. This is a local integration starter, not a live deployment.

## Install and start (PowerShell, from the repository root)

Install Python first if `python --version` is unavailable. The following installation
downloads the backend/test dependencies into a local virtual environment:

```powershell
python -m venv services/api/.venv
& services/api/.venv/Scripts/python.exe -m pip install -e 'services/api[test]'
```

No activation or PowerShell execution-policy change is necessary. Start the backend:

```powershell
& services/api/.venv/Scripts/python.exe -m uvicorn smart_basket.app:app --host 127.0.0.1 --port 8000
```

Open [interactive API documentation](http://localhost:8000/docs) or
[health](http://localhost:8000/api/health). In Swagger, execute **GET /api/context**
first; the browser keeps the demo cookie for subsequent requests. Paste
`fixtures/planning-request.json` into **POST /api/plans**. Use the returned `runId`
with **GET /api/plans/{runId}** to retrieve the result.

Stop the server with Ctrl+C. Do not use multiple workers. `--reload` is optional
during development but loses all demo state on each code change.

## Configuration

`.env.example` lists the supported variables. Defaults already work; `.env`
files are **not automatically loaded**. Set environment variables in PowerShell
before launch if changing them:

```powershell
$env:SMART_BASKET_MODE = 'demo'
$env:SMART_BASKET_CORS_ORIGINS = 'http://localhost:3000'
$env:SMART_BASKET_MEALS_SOURCE = 'synthetic'
```

Any mode other than `demo` fails startup. Use `localhost` consistently on both
browser services; mixing it with `127.0.0.1` breaks same-site cookie assumptions.
Bind only to loopback for this demo. A shared hosted URL is not supplied yet.
Live Edamam planning is not enabled until the actual account fields, attribution
rules and data-use permissions are verified. Required server-side names are
`EDAMAM_MEAL_PLANNER_APP_ID`, `EDAMAM_MEAL_PLANNER_APP_KEY`,
`EDAMAM_ACCOUNT_USER`, optional `EDAMAM_MEAL_PLANNER_BASE_URL` and
`EDAMAM_TIMEOUT_SECONDS` and `EDAMAM_SYNTHETIC_FALLBACK`. Keep fallback enabled
for demos unless the goal is to verify a hard live failure path.

## Ksiusha and Alina: HTTP connection

The frontend communicates with the Python API through Next.js rewrites. Browser
requests use same-origin `/api/...` URLs, and Next.js forwards them to the backend.

The current `apps/web/next.config.ts` configuration is:

```ts
import type { NextConfig } from "next";

const apiBaseUrl =
  process.env.API_BASE_URL ??
  "http://127.0.0.1:8000";

const config: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiBaseUrl}/api/:path*`,
      },
    ];
  },
};

export default config;
```

### Local launch

Start the Python backend first using the command from the **Install and start**
section above.

Then, in a second terminal, start the Next.js frontend from the repository root:

```powershell
cd apps/web
npm.cmd install
npm.cmd run dev
```

`npm.cmd install` is only required on the first launch or after dependency changes.

Open the frontend at `http://localhost:3000`.

Keep both the Python backend and the Next.js frontend running during local development.

```ts
// With the Next.js forwarding above...
// For direct local API access instead, set base = 'http://localhost:8000'.
const base = '';
async function api(path: string, body?: unknown, scenario?: string) {
  const response = await fetch(`${base}/api${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'include',
    headers: {
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(scenario ? { 'X-Demo-Scenario': scenario } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw data.error;
  return data;
}

await api('/context'); // Creates a server-generated demo session cookie.
const run = await api('/plans', planningRequest); // 202, queued snapshot
// Poll approximately every 2 seconds until completed/failed.
const snapshot = await api(`/plans/${run.runId}`);
// Only use snapshot.result after status === 'completed'.
const preview = await api('/cart/preview', {
  runId: snapshot.result.runId, version: snapshot.result.version,
});
// Show preview first. On the user's explicit confirmation:
const receipt = await api('/cart/confirm', {
  previewId: preview.previewId, idempotencyKey: crypto.randomUUID(),
});
```

Persist/reuse the confirmation key for retries of one action. The demo additionally
deduplicates repeat confirmations of the same preview, even with a different key.
Never send prices, product edits or account IDs in confirmation requests.

Cart and export flow:

| Action | Request | Result |
|---|---|---|
| Recalculate | `POST /api/plans/:runId/recalculate`, `{version, selectedRecurringIds}` | 202 new run; old previews become stale; new version increments |
| Cart preview | `POST /api/cart/preview`, `{runId, version}` | Existing quantities, additions, projected total and expiry |
| Cart confirm | `POST /api/cart/confirm`, `{previewId, idempotencyKey}` | Receipt: `success`, `partial` or `failed` |
| FatSecret status | `GET /api/integrations/fatsecret` | `connected: false`, `exportAvailable: true` **for simulation only**; show `reason` |
| FatSecret preview | `POST /api/fatsecret/exports/preview`, `{runId, version, mealIds}` | Personal portions, matches, unresolved foods, `canConfirm` |
| FatSecret confirm | `POST /api/fatsecret/exports/confirm`, `{previewId, idempotencyKey}` | 202 `{exportId}` |
| FatSecret outcome | `GET /api/fatsecret/exports/:exportId` | Poll until `success`, `partial` or `failed` |

Every API response carries `X-Data-Mode: demo`; the plan includes `dataMode`, products
include `source`, and operation payloads include demo warnings. OAuth start/callback
routes return 503 `INTEGRATION_UNAVAILABLE` until Arina supplies authentication.
An absent/unknown session yields 401; other sessions' IDs yield 404. Demo `/context`
is the documented exception that creates a session rather than requiring OAuth.

## Exercise error states

Set **X-Demo-Scenario on the planning or preview request**, not on confirmation:

| Request | Supported header values |
|---|---|
| `POST /api/plans` | `success` (default), `failed` (worker fails after 202) |
| `POST /api/cart/preview` | `success`, `partial`, `failed` |
| `POST /api/fatsecret/exports/preview` | `success`, `partial`, `failed`, `unmatched` |

Use a new plan per scenario; terminal operations are intentionally retained and
cannot be replayed with a different outcome. Partial cart confirmation succeeds
for the first product and fails the rest. Partial export saves the first selected
meal and fails the rest: select at least **two meals** to observe partial success.
`unmatched` makes `canConfirm: false`; confirmation returns 409 `UNRESOLVED_FOODS`.

Set `budgetMinor: 100` for an over-budget result, `days: 8` for 400 validation,
or send an outdated `version` for 409 `STALE_PLAN`. Only `vegetarian` preference and
`peanut-free` restriction labels are currently supported; unknown labels fail
validation. Calorie targets are retained and surfaced, but synthetic meals do not
optimize calories. Pet demand and notes are retained for the surrounding pipeline.

All request failures use `{error: {code, message, retryable}}`. Per-item failures are
successful HTTP responses containing operation outcomes, not an HTTP-level crash.
Cart `requestedQuantity` and `actualQuantity` mean the final cart quantity, including
pre-existing contents. Preview `afterQuantity - beforeQuantity` is the addition.

## Arina, Uliana and Vika: Python boundaries

- `create_app(planner=..., catalog=...)` is the injection point. See `demo.Planner`
  for Uliana's synchronous `run_planner` / `recalculate_plan` signatures. They run
  as in-process FastAPI background tasks after 202. Call `emit_progress(stage,
  message)` with completed facts. Return a `PlanningResult` or camelCase mapping.
  API owns session isolation, run IDs and versions. A separate AI server is not needed.
- `catalog.matching.CatalogReader` defines Arina's normalized `search_products`
  and `get_product_details` boundary. Adapt provider records to `ProductCandidate`
  before returning. Pass a composition evaluator through
  `MatchingContext.check_restrictions`; restricted demand stays unresolved without
  explicit evidence. App context additionally needs `get_user_context`.
- `find_product_candidates(ingredients, [], context)` returns `CandidateResult`
  with candidates and unresolved requirements. Unavailable/unknown/incompatible
  entries remain visible as evidence. Vika must select only available passing
  candidates with usable content conversion. `find_replacement` filters them.
- `purchase_quantity` converts compatible demand to selling units; `line_total`
  rounds money half-up. Combine all demand covered by one product before rounding.
  750 g / 500 g package = 2 packages × 6000 kopiykas = 12000, with 250 g surplus.
  Weighted example: 750 g / 1000 g per kg, 0.1 kg increment = 0.8 kg.
- Nonempty `selectedRecurring` currently raises an explicit unsupported error.
  Demo history is empty and recurring suggestions are `[]`. Vika's normalized
  recurring-demand input is still needed; the server rejects invented selection IDs.
- Sofiia's `meals/` module owns meal filters, serving scaling, synthetic fallback
  and the Edamam adapter boundary. The demo still labels synthetic meal data
  honestly and does not store provider recipe payloads.

Live mode is intentionally blocked. Real gateway writes, OAuth/token storage,
persistent operation journals, timeout reconciliation, provider food matching and
FatSecret app visibility must be implemented/verified before enabling it. Cart and
export services currently simulate deterministic outcomes in memory. Retrying a
partial operation returns its stored receipt; automated partial recovery is deferred.

## Verification and generated contracts

From the repository root:

```powershell
& services/api/.venv/Scripts/python.exe -m pytest services/api/tests -q -p no:cacheprovider
& services/api/.venv/Scripts/python.exe services/api/scripts/export_contracts.py --check
& services/api/.venv/Scripts/python.exe -m pip check
```

After an intentional model/fixture change, regenerate with:

```powershell
& services/api/.venv/Scripts/python.exe services/api/scripts/export_contracts.py
```

`packages/contracts/openapi.json` is the single portable API contract and contains
all endpoint schemas. `fixtures/manifest.json` maps each retained fixture to its
executable server model. Fixtures use stable invented IDs and a fixed example
timestamp; use actual API-returned IDs/expiry when exercising operations.
Frontend TypeScript types still belong to Ksiusha and must match these schemas.
