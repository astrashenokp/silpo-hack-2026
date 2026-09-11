import pytest

from smart_basket.agent.chat_models import (
    ChatCommand,
)

from smart_basket.agent.orchestrator import (
    UlianaPlanner,
)

from smart_basket.demo import (
    DemoCatalog,
)

from smart_basket.schemas import (
    PlanningRequest,
)

# ==========================================================
# FAKE GEMINI
# ==========================================================

class FakeChatInterpreter:
    """
    Pretends to be Gemini.

    We tell it in advance which ChatCommand
    it should return.
    """

    def __init__(self, command):
        self.command = command

    def interpret(self, message):
        return self.command.model_copy(
            update={
                "original_message": message
            }
        )


class BrokenChatInterpreter:
    """
    Simulates Gemini/API failure.
    """

    def interpret(self, message):
        raise RuntimeError(
            "Gemini unavailable"
        )


class FailIfCalledInterpreter:
    """
    Used to prove that button flows
    do NOT call Gemini.
    """

    def interpret(self, message):
        raise AssertionError(
            "Gemini must not be called"
        )


# ==========================================================
# TEST DATA
# ==========================================================

def make_request(
    budget_minor=180000,
):
    return PlanningRequest(
        budget_minor=budget_minor,
        currency="UAH",
        days=4,
        people=3,
        calories_per_person_per_day=2000,
        preferences=[
            "vegetarian"
        ],
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


def make_result(planner):
    return planner.run_planner(
        request=make_request(),
        session=object(),
        emit_progress=lambda *_: None,
    )

def test_create_button_runs_planner_without_gemini():

    planner = UlianaPlanner(
        catalog=DemoCatalog(),
        chat_interpreter=(
            FailIfCalledInterpreter()
        ),
    )

    result = planner.run_planner(
        request=make_request(),
        session=object(),
        emit_progress=lambda *_: None,
    )

    assert result.version == 1

    assert (
        result.budget_minor
        == 180000
    )

    assert (
        result.basket_total_minor
        == 49000
    )

    assert (
        result.budget_status
        == "within_budget"
    )

    assert len(
        result.meal_plan
    ) == 12

def test_chat_can_create_plan():
    planner = UlianaPlanner(
        catalog=DemoCatalog(),

        chat_interpreter=(
            FakeChatInterpreter(
                ChatCommand(
                    intent="create_plan"
                )
            )
        ),
    )

    result = planner.handle_chat_message(
        message="Створи кошик",

        previous_result=None,

        current_request=(
            make_request()
        ),

        session=object(),

        emit_progress=lambda *_: None,
    )

    assert (
        result.budget_minor
        == 180000
    )

    assert (
        result.basket_total_minor
        == 49000
    )

    assert result.version == 1

def test_chat_change_budget():

    catalog = DemoCatalog()

    first_planner = UlianaPlanner(
        catalog=catalog,
        chat_interpreter=(
            FailIfCalledInterpreter()
        ),
    )

    previous_result = (
        make_result(first_planner)
    )

    planner = UlianaPlanner(
        catalog=catalog,

        chat_interpreter=(
            FakeChatInterpreter(
                ChatCommand(
                    intent="change_budget",
                    budget_uah=1500,
                )
            )
        ),
    )

    result = planner.handle_chat_message(
        message=(
            "Зміни бюджет на 1500 грн"
        ),

        previous_result=(
            previous_result
        ),

        session=object(),

        emit_progress=lambda *_: None,
    )

    assert (
        result.budget_remaining_minor
        ==
        result.budget_minor
        - result.basket_total_minor
    )

def test_chat_explain_plan():

    catalog = DemoCatalog()

    first_planner = UlianaPlanner(
        catalog=catalog,
        chat_interpreter=(
            FailIfCalledInterpreter()
        ),
    )

    previous_result = (
        make_result(first_planner)
    )

    planner = UlianaPlanner(
        catalog=catalog,

        chat_interpreter=(
            FakeChatInterpreter(
                ChatCommand(
                    intent="explain_plan"
                )
            )
        ),
    )

    response = (
        planner.handle_chat_message(
            message="Поясни бюджет",

            previous_result=(
                previous_result
            ),

            session=object(),

            emit_progress=lambda *_: None,
        )
    )

    assert (
        response["type"]
        == "explanation"
    )

    assert (
        "1310.00 UAH"
        in response["message"]
    )

def test_chat_replace_ingredient():

    catalog = DemoCatalog()

    first_planner = UlianaPlanner(
        catalog=catalog,
        chat_interpreter=(
            FailIfCalledInterpreter()
        ),
    )

    previous_result = (
        make_result(first_planner)
    )

    planner = UlianaPlanner(
        catalog=catalog,

        chat_interpreter=(
            FakeChatInterpreter(
                ChatCommand(
                    intent=(
                        "replace_ingredient"
                    ),
                    ingredient="rice",
                )
            )
        ),
    )

    response = (
        planner.handle_chat_message(
            message="Заміни рис",

            previous_result=(
                previous_result
            ),

            session=object(),

            emit_progress=lambda *_: None,
        )
    )

    assert (
        response["type"]
        == "meal_replan_required"
    )

    matched_ingredient = next(
        ingredient
        for ingredient
        in previous_result.ingredients
        if ingredient.id
        == response["ingredientId"]
    )

    searchable_names = [
        matched_ingredient.name.lower(),
        *[
            term.lower()
            for term
            in matched_ingredient.search_terms
        ],
    ]

    assert any(
        "rice" in name
        or name in "rice"
        for name in searchable_names
    )

def test_chat_reduce_cost():

    catalog = DemoCatalog()

    first_planner = UlianaPlanner(
        catalog=catalog,
        chat_interpreter=(
            FailIfCalledInterpreter()
        ),
    )

    previous_result = (
        make_result(first_planner)
    )

    planner = UlianaPlanner(
        catalog=catalog,

        chat_interpreter=(
            FakeChatInterpreter(
                ChatCommand(
                    intent="reduce_cost",

                    preserve_meal_slots=[
                        "breakfast"
                    ],
                )
            )
        ),
    )

    response = (
        planner.handle_chat_message(
            message=(
                "Зроби дешевше, "
                "але не змінюй сніданки"
            ),

            previous_result=(
                previous_result
            ),

            session=object(),

            emit_progress=lambda *_: None,
        )
    )

    assert (
        response["type"]
        == "meal_replan_required"
    )

    assert (
        response[
            "preserveMealSlots"
        ]
        == ["breakfast"]
    )
def test_chat_unknown_command():

    catalog = DemoCatalog()

    first_planner = UlianaPlanner(
        catalog=catalog,
        chat_interpreter=(
            FailIfCalledInterpreter()
        ),
    )

    previous_result = (
        make_result(first_planner)
    )

    planner = UlianaPlanner(
        catalog=catalog,

        chat_interpreter=(
            FakeChatInterpreter(
                ChatCommand(
                    intent="unknown"
                )
            )
        ),
    )

    response = (
        planner.handle_chat_message(
            message="Замов мені таксі",

            previous_result=(
                previous_result
            ),

            session=object(),

            emit_progress=lambda *_: None,
        )
    )

    assert (
        response["type"]
        == "unsupported"
    )
def test_chat_handles_gemini_error():

    catalog = DemoCatalog()

    planner = UlianaPlanner(
        catalog=catalog,
        chat_interpreter=(
            BrokenChatInterpreter()
        ),
    )

    response = (
        planner.handle_chat_message(
            message="Зроби дешевше",

            previous_result=None,

            session=object(),

            emit_progress=lambda *_: None,
        )
    )

    assert (
        response["type"]
        == "chat_error"
    )

def test_recalculate_button_does_not_use_gemini():

    planner = UlianaPlanner(
        catalog=DemoCatalog(),

        chat_interpreter=(
            FailIfCalledInterpreter()
        ),
    )

    previous_result = (
        make_result(planner)
    )

    old_meal_ids = [
        meal.id
        for meal
        in previous_result.meal_plan
    ]

    result = planner.recalculate_plan(
        previous_result=(
            previous_result
        ),

        selected_recurring_ids=[],

        session=object(),

        emit_progress=lambda *_: None,
    )

    assert result.version == 2

    assert [
        meal.id
        for meal
        in result.meal_plan
    ] == old_meal_ids

    assert (
        result.basket_total_minor
        ==
        previous_result
        .basket_total_minor
    )
def test_chat_recalculate_plan():

    catalog = DemoCatalog()

    first_planner = UlianaPlanner(
        catalog=catalog,
        chat_interpreter=(
            FailIfCalledInterpreter()
        ),
    )

    previous_result = (
        make_result(first_planner)
    )

    planner = UlianaPlanner(
        catalog=catalog,

        chat_interpreter=(
            FakeChatInterpreter(
                ChatCommand(
                    intent="recalculate_plan"
                )
            )
        ),
    )

    result = planner.handle_chat_message(
        message="Перерахуй кошик",

        previous_result=(
            previous_result
        ),

        selected_recurring_ids=[],

        session=object(),

        emit_progress=lambda *_: None,
    )

    assert result.version == 2

    assert (
        result.basket_total_minor
        ==
        previous_result
        .basket_total_minor
    )
