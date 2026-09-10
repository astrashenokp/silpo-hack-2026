import pytest
from fastapi.testclient import TestClient

from smart_basket.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        client.get("/api/context")
        yield client


@pytest.fixture
def planning_request():
    return {"budgetMinor": 180000, "currency": "UAH", "days": 4, "people": 3,
            "caloriesPerPersonPerDay": 2000, "healthConditions": [],
            "cookingTimeLimit": None, "preferences": ["vegetarian"],
            "restrictions": [], "pets": [{"species": "cat", "count": 1}],
            "includeRecurring": True, "notes": ""}


def create_plan(client, request):
    queued = client.post("/api/plans", json=request)
    assert queued.status_code == 202, queued.text
    assert queued.json()["status"] == "queued"
    result = client.get(f"/api/plans/{queued.json()['runId']}").json()
    assert result["status"] == "completed", result
    return result["result"]
