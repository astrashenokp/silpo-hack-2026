# Deployment runbook (draft)

Owner: Polina. Status on September 12: the local Docker rehearsal below now passes end to end —
both images build, the API container reports healthy, `/api` forwarding works through the web
container, the full e2e suite (40 of 40) and the full Playwright UI suite (38 of 38, desktop and
Pixel 7) both pass against the running compose stack (BUG-001 was fixed in #20). One rehearsal
note: `PUBLIC_WEB_ORIGIN` must match the exact origin the browser uses, port included, or every
POST silently answers 403 `ORIGIN_NOT_ALLOWED` — hit this locally only because another,
unrelated project already held port 3000 on the test machine; the documented default setup
(`http://localhost:3000`) needs no such override. **No host is chosen yet**: that decision needs
a VM/PaaS account and a budget owner, which is outside what this repository or Polina alone can
supply. CI also builds both images on every pull request (`.github/workflows/ci.yml`, job
"Deployment images build").

## Topology

```text
Browser ──https──> Next.js web (public origin, :3000) ──/api/* rewrite──> Python API (:8000, one worker)
```

The browser talks only to the web origin. Session cookies, OAuth callbacks and every
`/api/...` call go through it; the API can stay private when the host allows it.

## Rules found during intake

1. `API_BASE_URL` is a **build-time** setting of the web app: it is baked into
   `.next/routes-manifest.json`, and `next start` ignores a runtime value. Rebuild the web
   image whenever the API address changes.
2. POSTs whose browser `Origin` is missing from `SMART_BASKET_CORS_ORIGINS` get
   403 `ORIGIN_NOT_ALLOWED`. Set it to the exact public web origin (scheme, host and port).
3. Run exactly **one** API instance with one worker. Sessions, plans, cart and export receipts
   and FatSecret tokens live in process memory: a restart or a second instance loses them.
   Disable sleep-on-idle on free tiers during rehearsals and recording.
4. `.env` files are not loaded by the API; provide real environment variables.
5. Register OAuth callbacks on the **web origin** (`https://<web-origin>/api/auth/.../callback`)
   so the browser sends the session cookie with the callback.
6. `SMART_BASKET_MODE` must be `demo`; any other value refuses to start.

## Environment variables

| Variable | Service | Hosted demo value | Secret |
|---|---|---|---|
| `API_BASE_URL` | web, **build time** | internal address of the API, e.g. `http://api:8000` | no |
| `SMART_BASKET_MODE` | api | `demo` | no |
| `SMART_BASKET_CORS_ORIGINS` | api | `https://<web-origin>` | no |
| `SMART_BASKET_FRONTEND_URL` | api | `https://<web-origin>` | no |
| `SILPO_MCP_URL` | api | default `https://mcp.silpo.ua/mcp` | no |
| `SILPO_OAUTH_CALLBACK_URL` | api | `https://<web-origin>/api/auth/silpo/callback` | no |
| `FATSECRET_CONSUMER_KEY`, `FATSECRET_CONSUMER_SECRET` | api | from Arina/Rina through a private channel | yes |
| `FATSECRET_OAUTH_CALLBACK_URL` | api | `https://<web-origin>/api/auth/fatsecret/callback` | no |
| `FATSECRET_TIMEOUT_SECONDS`, `FATSECRET_ALLOW_EDAMAM_EXPORT` | api | `10`, `false` until Sofiia confirms data use | no |
| `SMART_BASKET_MEALS_SOURCE`, `EDAMAM_SYNTHETIC_FALLBACK` | api | `edamam`, `true` so valid credentials use Edamam and provider failures remain recoverable | no |
| `EDAMAM_MEAL_PLANNER_APP_ID`, `EDAMAM_MEAL_PLANNER_APP_KEY`, `EDAMAM_ACCOUNT_USER` | api | from Sofiia, only for the live check | yes |

The root `.env.example` lists the same names. Never commit values; `deploy/.env.api` is
ignored by git through the root `.env.*` rule.

## Hosting options (decision pending)

| Option | How | Watch out for |
|---|---|---|
| A. One VM with Docker | `docker compose -f deploy/docker-compose.yml up --build -d`, TLS reverse proxy (e.g. Caddy) in front of `:3000` | VM access and a domain for HTTPS |
| B. Container PaaS, two services | Build `deploy/web.Dockerfile` and `deploy/api.Dockerfile`; web build argument `API_BASE_URL` = the API's private URL | Single always-on API instance; private networking may need a paid plan |
| C. Vercel web + PaaS API | Set `API_BASE_URL` in the Vercel build environment | The API must be reachable from Vercel servers; rebuild the web app when it moves |

Choose by: an always-on single API instance, a stable HTTPS origin for OAuth callbacks,
and no cost surprises before September 14.

## Local rehearsal with Docker

```powershell
# Optional: secrets for live checks, one KEY=value per line
notepad deploy/.env.api
docker compose -f deploy/docker-compose.yml up --build
```

Open `http://localhost:3000`. Stop with Ctrl+C; `docker compose -f deploy/docker-compose.yml down`
removes the containers (and all demo state).

## After every deploy

1. `curl https://<web-origin>/api/health` returns `{"status":"ok","mode":"demo"}`.
2. `E2E_BASE_URL=https://<web-origin>` then `python -m pytest tests/e2e` passes (known
   `xfail` items only).
3. In a signed-out browser: run the golden input, preview and confirm the cart, connect
   FatSecret and return to the app through the callback.
4. Record URL, revision and time in `docs/handoffs/polina.md`.

## Recovery

- API restarted: every session and plan is gone. Reload the page and create the plan again;
  reconnect FatSecret.
- Every POST fails with 403: the page was opened from an origin that is not in
  `SMART_BASKET_CORS_ORIGINS`.
- Wrong API behind `/api`: rebuild the web app with the right `API_BASE_URL`.
- Bad release: redeploy the frozen revision recorded in the handoff.
