# Integration intake — September 10 branch status

This is the current branch handoff for Polina's September 12 intake, **not a
release-ready declaration**. The active review branch is `sofiia-meal-planning`.
Rina's demo backend is implemented locally; Uliana's orchestration, Vika's
optimization and Sofiia's meal-planning module are connected in the backend
pipeline.

Start with [Rina's handoff](rina.md) and the [backend launch guide](../../services/api/README.md).
Backend: Python 3.12+, local `.venv`, Uvicorn port 8000, one worker. Health:
`GET /api/health`. Initialize a demo session with `GET /api/context`. The
Next.js frontend lives in `apps/web`, forwards `/api/...` to the backend and can
display the completed planning flow, including meal cards, calorie summary,
warnings, aggregate ingredients and selected basket products.

Available: validated HTTP contracts; synthetic planning, cart and Saved Meal
operations; product matching helpers; Sofiia `meal-plan`/`ingredients` fixtures
under `fixtures/`; 119 passing backend tests. All external providers remain
unverified in live mode, and `SMART_BASKET_MODE=live` deliberately refuses
startup. No credentials or external account access are necessary for this demo.

Before final intake, record the exact merged revision, replace/verify Arina's
providers and auth, verify live Edamam/FatSecret permissions, persist
session/operation state, implement uncertain-write reconciliation, and record
actual FatSecret account/app and data-use evidence. Each author retains ownership
of these unfinished pieces. Final end-to-end QA remains Polina's work from
September 12. Receiver verification and shared hosted URL are pending.
