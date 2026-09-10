from fastapi.testclient import TestClient

from smart_basket.agent import UlianaPlanner
from smart_basket.app import create_app
from smart_basket.demo import DemoCatalog
from smart_basket.meals.nutrition import build_nutrition_summary
from smart_basket.schemas import IngredientAmount, IngredientRequirement, Meal, UserContext


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


def test_uliana_marks_edamam_meals_as_mixed_and_blocks_demo_cart(monkeypatch):
    def fake_meal_plan(request, effective_context):
        meal = Meal(
            id="edamam-day-1-breakfast-oats",
            day=1,
            slot="breakfast",
            title="Live oats",
            servings=request.people,
            kcal_per_serving=200.0,
            calorie_target=None,
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

    assert result["dataMode"] == "mixed"
    assert result["canConfirmCart"] is False
    assert "cart confirmation is disabled" in " ".join(result["warnings"])
    assert client.post(
        "/api/cart/preview",
        json={"runId": result["runId"], "version": result["version"]},
    ).status_code == 409
