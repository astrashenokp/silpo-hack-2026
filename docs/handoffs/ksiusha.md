# Handoff: Ksiusha — Next.js planner frontend

- Date: September 10, 2026.

- Revision: `feature/ksiusha-frontend`; frontend implementation ready for integration with result components.

- Receivers: Alina for result/cart component integration; Rina for API contract verification; Arina for provider connection flows.

- Status: planner input and backend planning flow are ready; Alina's result presentation integration remains pending.

The Next.js frontend contains the planner page shell, input form, profile/context
summary and planning flow. The form collects budget, days, people, calories,
preferences, restrictions, pets and recurring-purchase settings. Input validation
runs before submission, and the budget is converted from UAH to integer kopiykas
before the `PlanningRequest` is sent.

Frontend API calls use relative `/api/...` paths. Next.js forwards them to the
Python backend configured through `API_BASE_URL`; the local demo default is
`http://127.0.0.1:8000`. The frontend loads `/api/context`, submits a plan through
`POST /api/plans`, stores the returned `runId` and polls the corresponding run
until it reaches `completed` or `failed`. Duplicate submissions are blocked while
a plan is running, polling stops on terminal states or component cleanup, and
responses from an older run cannot overwrite a newer run.

The frontend uses typed `PlanningRequest`, `RunSnapshot` and `PlanningResult`
contracts in `apps/web/src/lib/api/planner.ts`. A completed snapshot is passed
from `PlannerForm` to `page.tsx` through `onPlanReady`, where it is available for
the result components.

Profile/context information is displayed separately from editable form values, so
a late context response does not overwrite user input. Missing or expired demo
sessions produce a recovery state in the UI and can be restored before retrying
the request. Backend errors and planning progress/failure states are also displayed.

Main code: `apps/web/src/app/page.tsx`,
`apps/web/src/features/planner-input/PlannerForm.tsx`,
`apps/web/src/features/planner-input/ContextSummary.tsx`,
`apps/web/src/lib/api/planner.ts`, `apps/web/next.config.ts` and
`apps/web/.env.example`.

Current verification: valid planner submission and normalized request, UAH-to-kopiykas
conversion, input validation, context loading, completed planning flow, terminal
polling, stale-run protection, expired-session recovery and configurable backend
forwarding were checked against the local demo API. The layout was checked on
desktop, approximately 768 px and 375 px widths. Keyboard Tab navigation and form
submission with Enter were also checked.

Known limitations: Alina's result/menu/cart presentation components are not available
yet, so the current Smart Basket presentation remains a placeholder and is not wired
to the completed `PlanningResult`. Final result-screen integration and its responsive
QA therefore remain pending. FatSecret live connection behavior also depends on
Arina's provider/auth flow and must not block normal planning while disconnected.

Next connection: Alina supplies the result/menu/cart components; Ksiusha mounts them
using the completed `PlanningResult` already available in `page.tsx` and performs
final integration QA. Provider connection UI is connected to Arina's flow when its
live contract is available.

Receiving teammate verification: pending.