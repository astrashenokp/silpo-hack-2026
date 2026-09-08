"""
Тести для optimization/recurrence.py і optimization/optimizer.py.
Запуск: python -m pytest services/api/tests/test_optimization.py -v
(або разом з усіма іншими тестами, вони підхопляться автоматично)
"""

from datetime import date

from smart_basket.catalog.matching import MatchingContext
from smart_basket.optimization.optimizer import optimize_basket
from smart_basket.optimization.recurrence import analyze_recurring
from smart_basket.schemas import (
    CandidateResult,
    IngredientRequirement,
    Pet,
    PlanningRequest,
    ProductCandidate,
    UnresolvedRequirement,
)


def make_planning_request(budget_minor: int) -> PlanningRequest:
    return PlanningRequest(
        budget_minor=budget_minor, currency="UAH", days=4, people=3,
        calories_per_person_per_day=None, preferences=[], restrictions=[],
        pets=[], include_recurring=True, notes="",
    )


# ---------------------------------------------------------------
# Частина A: analyze_recurring
# ---------------------------------------------------------------

def test_empty_history_returns_no_suggestions():
    assert analyze_recurring([], [], date(2026, 9, 10)) == []


def test_sparse_history_below_threshold_is_ignored():
    purchases = [
        {"receiptId": "r1", "purchasedAt": "2026-08-01T10:00:00+03:00",
         "productId": "p1", "name": "Молоко 1л", "category": "dairy",
         "quantity": 1, "unit": "piece"},
        {"receiptId": "r2", "purchasedAt": "2026-08-15T10:00:00+03:00",
         "productId": "p1", "name": "Молоко 1л", "category": "dairy",
         "quantity": 1, "unit": "piece"},
    ]  # лише 2 дати, поріг MIN_DISTINCT_DATES=3 не досягнутий
    assert analyze_recurring(purchases, [], date(2026, 9, 10)) == []


def test_duplicate_dates_do_not_count_twice():
    # Два чеки в один день -> це ОДНА точка даних, а не дві
    purchases = [
        {"receiptId": "r1", "purchasedAt": "2026-08-01T09:00:00+03:00",
         "productId": "p1", "name": "Хліб", "category": "bakery",
         "quantity": 1, "unit": "piece"},
        {"receiptId": "r2", "purchasedAt": "2026-08-01T18:00:00+03:00",
         "productId": "p1", "name": "Хліб", "category": "bakery",
         "quantity": 1, "unit": "piece"},
        {"receiptId": "r3", "purchasedAt": "2026-08-15T10:00:00+03:00",
         "productId": "p1", "name": "Хліб", "category": "bakery",
         "quantity": 1, "unit": "piece"},
    ]
    # 2 унікальні дати (1 і 15 серпня) -> нижче порогу 3, нічого не повертаємо
    assert analyze_recurring(purchases, [], date(2026, 9, 10)) == []


def test_known_recurrence_produces_reproducible_suggestion():
    purchases = [
        {"receiptId": "r1", "purchasedAt": "2026-08-01T10:00:00+03:00",
         "productId": "p-cat-1", "name": "Корм для кота 2кг", "category": "pet-food",
         "quantity": 1, "unit": "piece", "species": "cat"},
        {"receiptId": "r2", "purchasedAt": "2026-08-15T10:00:00+03:00",
         "productId": "p-cat-1", "name": "Корм для кота 2кг", "category": "pet-food",
         "quantity": 1, "unit": "piece", "species": "cat"},
        {"receiptId": "r3", "purchasedAt": "2026-08-29T10:00:00+03:00",
         "productId": "p-cat-1", "name": "Корм для кота 2кг", "category": "pet-food",
         "quantity": 1, "unit": "piece", "species": "cat"},
    ]
    pets = [Pet(species="cat", count=1)]
    result_1 = analyze_recurring(purchases, pets, date(2026, 9, 10))
    result_2 = analyze_recurring(purchases, pets, date(2026, 9, 10))
    # Однакові вхідні дані + однакова дата -> однаковий результат (відтворюваність)
    assert result_1 == result_2
    assert len(result_1) == 1
    assert result_1[0].selected is False


def test_pet_species_not_selected_is_filtered_out():
    purchases = [
        {"receiptId": "r1", "purchasedAt": "2026-08-01T10:00:00+03:00",
         "productId": "p-dog-1", "name": "Корм для собаки 3кг", "category": "pet-food",
         "quantity": 1, "unit": "piece", "species": "dog"},
        {"receiptId": "r2", "purchasedAt": "2026-08-15T10:00:00+03:00",
         "productId": "p-dog-1", "name": "Корм для собаки 3кг", "category": "pet-food",
         "quantity": 1, "unit": "piece", "species": "dog"},
        {"receiptId": "r3", "purchasedAt": "2026-08-29T10:00:00+03:00",
         "productId": "p-dog-1", "name": "Корм для собаки 3кг", "category": "pet-food",
         "quantity": 1, "unit": "piece", "species": "dog"},
    ]
    # Користувач обрав лише кота -> собачий корм не пропонується
    result = analyze_recurring(purchases, [Pet(species="cat", count=1)], date(2026, 9, 10))
    assert result == []


# ---------------------------------------------------------------
# Частина B: optimize_basket
# ---------------------------------------------------------------

def _oats_candidate(price=6000, available=True, restriction="pass", regular=None):
    return ProductCandidate(
        id="demo-oats", name="Demo dry oats, 500 g", requirement_ids=["oats"],
        price_minor=price, selling_unit="package", quantity_step=1.0,
        content_quantity=500.0, content_unit="g", available=available,
        restriction_check=restriction, regular_price_minor=regular,
        source="synthetic", checked_at="2026-09-07T12:00:00+00:00",
    )


def _oats_requirement(quantity=750.0):
    return [IngredientRequirement(
        id="oats", name="Dry oats", search_terms=["oats"], quantity=quantity,
        unit="g", meal_ids=["m1"], restrictions=[],
    )]


def test_package_rounding_two_packages_needed():
    """750 г потрібно, пакунок 500 г -> 2 пакунки, 12000 коп (приклад з CONTRACTS.md)."""
    candidates = CandidateResult(candidates=[_oats_candidate()], unresolved_requirements=[])
    result = optimize_basket(make_planning_request(100000), _oats_requirement(), candidates, [])
    assert len(result.selected_products) == 1
    sel = result.selected_products[0]
    assert sel.quantity == 2.0
    assert sel.line_total_minor == 12000
    assert result.budget_status == "within_budget"


def test_cheaper_alternative_is_chosen():
    """Серед двох придатних кандидатів обирається дешевший за повну потрібну кількість."""
    expensive = _oats_candidate(price=6000)
    cheaper = _oats_candidate(price=5000)
    cheaper.id = "demo-oats-cheap"
    candidates = CandidateResult(candidates=[expensive, cheaper], unresolved_requirements=[])
    result = optimize_basket(make_planning_request(100000), _oats_requirement(), candidates, [])
    assert result.selected_products[0].product_id == "demo-oats-cheap"
    assert result.selected_products[0].line_total_minor == 10000


def test_impossible_budget_returns_honest_over_budget():
    candidates = CandidateResult(candidates=[_oats_candidate()], unresolved_requirements=[])
    result = optimize_basket(make_planning_request(5000), _oats_requirement(), candidates, [])
    assert result.budget_status == "over_budget"
    assert result.budget_remaining_minor == 5000 - 12000
    # Позицію НЕ приховуємо навіть при перевищенні бюджету:
    assert len(result.selected_products) == 1


def test_restricted_product_is_rejected_not_selected():
    """restrictionCheck='fail' -> кандидат відхиляється, вимога лишається unresolved."""
    failing = _oats_candidate(restriction="fail")
    candidates = CandidateResult(candidates=[failing], unresolved_requirements=[])
    result = optimize_basket(make_planning_request(100000), _oats_requirement(), candidates, [])
    assert result.selected_products == []
    assert len(result.unresolved_requirements) == 1
    assert result.budget_status == "incomplete"


def test_unavailable_product_is_rejected():
    unavailable = _oats_candidate(available=False)
    candidates = CandidateResult(candidates=[unavailable], unresolved_requirements=[])
    result = optimize_basket(make_planning_request(100000), _oats_requirement(), candidates, [])
    assert result.selected_products == []
    assert result.budget_status == "incomplete"


def test_verified_promo_price_produces_savings():
    promo = _oats_candidate(price=5000, regular=6000)
    candidates = CandidateResult(candidates=[promo], unresolved_requirements=[])
    result = optimize_basket(make_planning_request(100000), _oats_requirement(), candidates, [])
    assert result.savings_minor == 2000  # (6000-5000) * 2 пакунки


def test_no_baseline_means_savings_is_null():
    candidates = CandidateResult(candidates=[_oats_candidate()], unresolved_requirements=[])
    result = optimize_basket(make_planning_request(100000), _oats_requirement(), candidates, [])
    assert result.savings_minor is None  # немає перевіреної бази -> null, а не 0


def test_already_unresolved_by_rina_is_not_duplicated():
    """Якщо Ріна вже позначила requirement нерозв'язаним - ми не додаємо його вдруге."""
    candidates = CandidateResult(
        candidates=[],
        unresolved_requirements=[UnresolvedRequirement(requirement_id="oats", reason="no match")],
    )
    result = optimize_basket(make_planning_request(100000), _oats_requirement(), candidates, [])
    assert len(result.unresolved_requirements) == 1