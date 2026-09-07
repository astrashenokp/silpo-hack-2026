# Integration intake — preliminary, September 7

This is a starting handoff for Polina's September 12 intake, **not a release-ready
declaration**. No shared revision or merged PR is recorded yet. Rina's mock backend
is implemented locally; all other modules are pending their authors' delivery.

Start with [Rina's handoff](rina.md) and the [backend launch guide](../../services/api/README.md).
Backend: Python 3.12+, local `.venv`, Uvicorn port 8000, one worker. Health:
`GET /api/health`. Initialize a demo session with `GET /api/context`. Frontend is
not implemented; Ksiusha must supply its installation/start commands and verify the
documented `/api/...` forwarding on port 3000 before a combined launch is possible.

Available: validated HTTP contracts; mock planning, cart and Saved Meal operations;
product matching helpers; fixtures under `fixtures/`; 42 passing backend tests.
All providers remain mocked, and `SMART_BASKET_MODE=live` deliberately refuses
startup. No credentials or external account access are necessary for this demo.

Before final intake, record the exact shared revision, install/start the frontend,
replace/verify Arina's providers and auth, connect Uliana/Sofiia/Vika's modules,
persist session/operation state, implement uncertain-write reconciliation, and
record actual FatSecret account/app and data-use evidence. Each author retains
ownership of these unfinished pieces. Final end-to-end QA remains Polina's work
from September 12. Receiver verification and shared hosted URL are pending.
