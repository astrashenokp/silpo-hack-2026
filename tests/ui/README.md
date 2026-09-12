# Browser QA: Playwright, axe and Lighthouse

Owner: Polina. Checks the web app in a real browser. Nothing here starts the stack;
point `UI_BASE_URL` at a running app (default `http://localhost:3000`, or the deployed
origin after a deploy).

## Setup (once, PowerShell)

```powershell
cd tests/ui
npm.cmd ci
npx.cmd playwright install chromium
```

## Run

Start the backend and the frontend first (see `services/api/README.md`), then in `tests/ui`:

| Command | What it does |
|---|---|
| `npm.cmd test` | All specs on two projects: `desktop` (Desktop Chrome) and `mobile` (Pixel 7) |
| `npm.cmd run test:desktop`, `npm.cmd run test:mobile` | One project only |
| `npm.cmd run report` | HTML report with screenshots, traces and axe JSON attachments |
| `npm.cmd run lighthouse`, `npm.cmd run lighthouse:mobile` | Lighthouse audit in Playwright's Chromium; reports in `reports/lighthouse/` |

## Specs

| File | Checks |
|---|---|
| `specs/smoke.spec.ts` | Guest path to the planner form without console errors; the account gate works with Tab and Enter |
| `specs/api-wiring.spec.ts` | Creating a plan sends `POST /api/plans` (regression check for BUG-002) |
| `specs/flows.spec.ts` | Against the running API: empty-budget validation; demo label and no horizontal overflow; the plan shows every requested day and the chosen products; recalculation adds the next plan version; a chat message is answered by the agent route; FatSecret save with a one-portion preview and outcome; adding opens the cart preview before anything changes; the cart panel and its sync control are reachable at every width; the preview can be confirmed into a receipt; an over-budget plan cannot be added; no invented name or regular purchases. No `test.fail` markers remain |
| `specs/a11y.spec.ts` | axe WCAG 2.1 AA scan of the account gate and the planner form. Fails on new serious or critical rules; known ones (`KNOWN_ISSUES`, BUG-009 color contrast) are annotated |

Known issues are tracked in `docs/qa/bugs.md`. When one is fixed, remove its `test.fail`
or `KNOWN_ISSUES` entry so the check protects against a regression.
