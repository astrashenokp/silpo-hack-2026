import json

from smart_basket.agent import UlianaPlanner
from smart_basket.demo import DemoCatalog
from smart_basket.schemas import PlanningRequest


def print_progress(stage, message):
    print(f"[{stage}] {message}")


def main():
    catalog = DemoCatalog()
    planner = UlianaPlanner(catalog)

    request = PlanningRequest(
        budget_minor=180000,
        currency="UAH",
        days=4,
        people=3,
        calories_per_person_per_day=2000,
        preferences=["vegetarian"],
        restrictions=[],
        pets=[
            {
                "species": "cat",
                "count": 1,
            }
        ],
        include_recurring=True,
        notes="",
    )

    result = planner.run_planner(
        request=request,
        session=None,
        emit_progress=print_progress,
    )

    print("\n===== PLANNING RESULT =====")

    print(
        json.dumps(
            result.model_dump(
                mode="json",
                by_alias=True,
            ),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()