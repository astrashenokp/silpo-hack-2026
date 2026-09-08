# Handoff: Vika — Recurring purchases & budget optimization

- Date: September 8, 2026.
- Revision: direct commit to `main`; ready for pipeline consumption.
- Receivers: Uliana (AI 4.1), Rina (Backend 3.2), Sofiia (AI 4.2).
- Status: module complete and tested; ready for orchestration and session integration.

The optimization module provides recurring purchase analysis and cost-effective basket
selection. It analyses past purchase patterns to suggest recurring items, checks
price/quantity tradeoffs, handles pack rounding, and optimizes total spend against
a budget ceiling without failing on unresolved requirements.

Contracts and data models follow Pydantic schemas in `smart_basket.schemas` (`ProductCandidate`,
`ProductSelection`, `RecurringSuggestion`, `CandidateResult`, `PlanningRequest`). Calculation
rules strictly import `purchase_quantity` and `line_total` from `smart_basket.catalog.matching`
to eliminate rounding discrepancies across backend boundaries.

Main code: `services/api/src/smart_basket/optimization/` (`__init__.py`, `recurrence.py`,
`optimizer.py`). Unit tests and regression coverage are in `services/api/tests/test_optimization.py`.
Fixture examples: `fixtures/recurring-items.json` and `fixtures/optimization-result.json`.

Public interface for Uliana:
- `analyze_recurring(purchases: list[dict], pets: list[Pet], as_of: date) -> list[RecurringSuggestion]`
- `optimize_basket(request: PlanningRequest, ingredients: list[IngredientRequirement], candidates: CandidateResult, selected_recurring: list[RecurringSuggestion]) -> OptimizationResult`

Current verification: 55 passing tests (42 existing suite + 13 new optimization unit
tests). Verification command:
`& services/api/.venv/Scripts/python.exe -m pytest services/api/tests -q -p no:cacheprovider`
All test suites pass cleanly with green status.

Known limitations: recurring candidate lookup in `find_product_candidates()` currently awaits
normalized requirements from catalog; absent candidates are safely collected in
`unresolvedRequirements` (status: `incomplete`) without triggering unhandled exceptions.

Next connections: Uliana integrates `analyze_recurring` and `optimize_basket` directly
into the agent planner flow; Rina connects real catalog matches instead of mocks.

Receiving teammate verification: pending integration by Uliana and Rina.