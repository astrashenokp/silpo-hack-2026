# Handoff: Vika — Recurring purchases & budget optimization

- Date: September 8, 2026.
- Revision: direct commit to `main`; ready for pipeline consumption.
- Receivers: Uliana (AI 4.1), Rina (Backend 3.2), Sofiia (AI 4.2).
- Status: recurrence and optimization modules are implemented and locally tested; recurring
	candidate lookup and plan recalculation remain integration responsibilities for Rina/Uliana.

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

Current verification: 15 focused optimization tests pass locally. Full-suite verification
also requires installing the service dependencies, including `httpx2`. Verification command:
`& services/api/.venv/Scripts/python.exe -m pytest services/api/tests -q -p no:cacheprovider`
The focused command is:
`$env:PYTHONPATH='services/api/src'; & services/api/.venv/Scripts/python.exe -m pytest --noconftest services/api/tests/test_optimization.py -q -p no:cacheprovider`

Known limitations: recurring candidate lookup in `find_product_candidates()` currently awaits
normalized requirements from catalog. The optimizer supports normalized recurring candidate
links and avoids charging a product twice when meal demand already selects it; Rina must still
provide those links. Uliana must pass selected recurring IDs through recalculation.

Next connections: Uliana integrates `analyze_recurring` and `optimize_basket` directly
into the agent planner flow; Rina connects real catalog matches instead of mocks.

Receiving teammate verification: pending integration by Uliana and Rina.