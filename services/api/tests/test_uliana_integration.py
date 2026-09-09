from fastapi.testclient import TestClient

from smart_basket.agent import UlianaPlanner
from smart_basket.app import create_app
from smart_basket.demo import DemoCatalog


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
    assert result["basketTotalMinor"] == 34000
    assert result["budgetRemainingMinor"] == 146000

    assert result["budgetStatus"] == "within_budget"

    assert len(result["mealPlan"]) == 12
    assert len(result["ingredients"]) == 3
    assert len(result["selectedProducts"]) == 3

    assert result["unresolvedRequirements"] == []
    assert result["canConfirmCart"] is True