import pytest
from fastapi.testclient import TestClient

from smart_basket.agent import UlianaPlanner
from smart_basket.agent.orchestrator import cart_confirmable
from smart_basket.app import create_app
from smart_basket.demo import DemoCatalog
from smart_basket.meals.nutrition import build_nutrition_summary
from smart_basket.schemas import (
    IngredientAmount, IngredientRequirement, Meal, ProductSelection, UserContext,
)


def _product(source, product_id="p1"):
    return ProductSelection(
        product_id=product_id, name="Item", requirement_ids=["r1"], recurring_suggestion_ids=[],
        quantity=1.0, selling_unit="package", unit_price_minor=100, line_total_minor=100,
        source=source, reason="test", restriction_check="pass",
    )


def _ready_context():
    return UserContext(preferences=[], restrictions=[], pets=[], history_available=False,
        cart_context_ready=True, warnings=[])


@pytest.mark.parametrize(
    "data_mode,sources,expected",
    [
        ("demo", ["synthetic"], True),
        # The case this run's fix unblocks: live/mixed meals, still-synthetic products.
        ("mixed", ["synthetic"], True),
        ("live", ["silpo"], True),
        ("mixed", ["silpo"], True),
        # A genuinely incoherent mix of sources in one basket must still be refused — neither
        # cart-write path (live or demo) could handle it.
        ("mixed", ["silpo", "synthetic"], False),
        ("demo", [], False),
    ],
)
def test_cart_confirmable_depends_on_product_source_not_data_mode(data_mode, sources, expected):
    products = [_product(source, product_id=f"p{i}") for i, source in enumerate(sources)]
    assert cart_confirmable(
        data_mode=data_mode, selected_products=products, budget_status="within_budget",
        unresolved_requirements=[], context=_ready_context(),
    ) is expected


def test_cart_confirmable_still_requires_budget_completeness_and_cart_context():
    products = [_product("synthetic")]
    base = dict(data_mode="demo", selected_products=products, context=_ready_context())
    assert cart_confirmable(budget_status="within_budget", unresolved_requirements=[], **base)
    assert not cart_confirmable(budget_status="over_budget", unresolved_requirements=[], **base)
    assert not cart_confirmable(budget_status="within_budget", unresolved_requirements=["x"], **base)
    not_ready = _ready_context().model_copy(update={"cart_context_ready": False})
    assert not cart_confirmable(
        data_mode="demo", selected_products=products, budget_status="within_budget",
        unresolved_requirements=[], context=not_ready,
    )


def test_live_cart_can_confirm_found_products_when_other_ingredients_are_unresolved():
    base = dict(
        data_mode="mixed",
        selected_products=[_product("silpo")],
        unresolved_requirements=["not-found"],
        context=_ready_context(),
    )
    assert cart_confirmable(budget_status="incomplete", **base)
    assert not cart_confirmable(budget_status="over_budget", **base)

    base["selected_products"] = [_product("synthetic")]
    assert not cart_confirmable(budget_status="incomplete", **base)


def test_uliana_planner_through_api():
    # 1. Створюємо demo catalog Ріни
    catalog = DemoCatalog()

    # 2. Підключаємо МОЮ orchestration замість DemoPlanner
    planner = UlianaPlanner(catalog)

    # 3. Створюємо справжній FastAPI app,
    # але передаємо йому UlianaPlanner
    app = create_app(
        planner=planner,
        catalog=catalog,
    )

    client = TestClient(app)

    # Створюємо demo session, як це роблять тести Ріни
    context_response = client.get("/api/context")
    assert context_response.status_code == 200


    # 4. Це запит, який умовно міг би надіслати frontend
    request_data = {
        "budgetMinor": 180000,
        "currency": "UAH",
        "days": 4,
        "people": 3,
        "caloriesPerPersonPerDay": 2000,
        "preferences": ["vegetarian"],
        "restrictions": [],
        "pets": [
            {
                "species": "cat",
                "count": 1,
            }
        ],
        "includeRecurring": True,
        "notes": "",
    }

    # 5. Відправляємо справжній HTTP-запит у FastAPI
    response = client.post(
        "/api/plans",
        json=request_data,
    )

    # 6. Перевіряємо, що API прийняв запит
    assert response.status_code in (200, 201, 202)

    created_plan = response.json()

    # API має створити справжній runId
    assert "runId" in created_plan

    run_id = created_plan["runId"]

    # 7. Отримуємо створений план через API
    response = client.get(f"/api/plans/{run_id}")

    assert response.status_code == 200

    plan = response.json()

    print("\n===== API RESULT =====")
    print(plan)

    # 8. Перевіряємо основні результати
    assert plan["status"] == "completed"

    result = plan["result"]

    assert result["budgetMinor"] == 180000
    assert result["basketTotalMinor"] == 49000
    assert result["budgetRemainingMinor"] == 131000

    assert result["budgetStatus"] == "within_budget"

    assert len(result["mealPlan"]) == 12
    assert len(result["ingredients"]) == 3
    assert len(result["selectedProducts"]) == 3

    assert result["unresolvedRequirements"] == []
    assert result["canConfirmCart"] is True


def test_uliana_reports_unsupported_context_restriction():
    class RestrictedCatalog(DemoCatalog):
        def get_user_context(self, session):
            return UserContext(
                preferences=[],
                restrictions=["wheat-free"],
                pets=[],
                history_available=False,
                cart_context_ready=True,
                warnings=[],
            )

    catalog = RestrictedCatalog()
    app = create_app(
        planner=UlianaPlanner(catalog),
        catalog=catalog,
    )

    client = TestClient(app)
    client.get("/api/context")

    response = client.post(
        "/api/plans",
        json={
            "budgetMinor": 180000,
            "currency": "UAH",
            "days": 1,
            "people": 1,
            "caloriesPerPersonPerDay": None,
            "preferences": [],
            "restrictions": [],
            "pets": [],
            "includeRecurring": False,
            "notes": "",
        },
    )

    run = client.get(f"/api/plans/{response.json()['runId']}").json()

    assert run["status"] == "failed"
    assert run["error"]["code"] == "VALIDATION_ERROR"
    assert "wheat-free" in run["error"]["message"]


def test_uliana_marks_edamam_meals_as_mixed_and_allows_the_demo_cart(monkeypatch):
    def fake_meal_plan(request, effective_context):
        meal = Meal(
            id="edamam-day-1-breakfast-oats",
            day=1,
            slot="breakfast",
            title="Live oats",
            servings=request.people,
            kcal_per_serving=200.0,
            macros_per_serving=None,
            calorie_target=None,
            cooking_time_minutes=None,
            ingredient_ids=["oats"],
            ingredient_amounts=[
                IngredientAmount(
                    ingredient_id="oats",
                    name="Dry oats",
                    quantity=50.0 * request.people,
                    unit="g",
                )
            ],
            source="edamam",
            source_url="https://recipes.test/oats",
            attribution="Recipe data powered by Edamam.",
        )
        return {
            "meals": [meal],
            "nutrition_summary": build_nutrition_summary(request, [meal]),
            "ingredients": [
                IngredientRequirement(
                    id="oats",
                    name="Dry oats",
                    search_terms=["oats"],
                    quantity=50.0 * request.people,
                    unit="g",
                    meal_ids=[meal.id],
                    restrictions=[],
                )
            ],
            "warnings": [],
            "source": "edamam",
        }

    monkeypatch.setattr("smart_basket.agent.orchestrator.build_meal_plan", fake_meal_plan)

    app = create_app()
    client = TestClient(app)
    client.get("/api/context")
    response = client.post(
        "/api/plans",
        json={
            "budgetMinor": 180000,
            "currency": "UAH",
            "days": 1,
            "people": 2,
            "caloriesPerPersonPerDay": None,
            "preferences": [],
            "restrictions": [],
            "pets": [],
            "includeRecurring": False,
            "notes": "",
        },
    )
    run = client.get(f"/api/plans/{response.json()['runId']}").json()
    result = run["result"]

    # "Mixed" (live meals, demo catalog) still discloses honestly in the warning text and the
    # dataMode field; it no longer blocks a complete, in-budget, fully-resolved plan from
    # reaching the demo cart, since the products backing it are unambiguously synthetic either
    # way — same as a fully-demo plan. Relaxed 2026-09-14 at Polina's explicit direction once
    # live Edamam meals became the shipped configuration; see cart_confirmable()'s docstring.
    assert result["dataMode"] == "mixed"
    assert result["canConfirmCart"] is True
    assert "Meal data is live or mixed while catalog/cart data remains demo." in result["warnings"]
    assert "cart confirmation is disabled" not in " ".join(result["warnings"])
    assert client.post(
        "/api/cart/preview",
        json={"runId": result["runId"], "version": result["version"]},
    ).status_code == 200
