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
class FakeMealReplanner:
    def __init__(
        self,
        previous_result,
    ):
        self.previous_result = (
            previous_result
        )

        self.calls = []

    def __call__(
        self,
        request,
        effective_context,
        previous_meals,
        reason,
        preserve_meal_slots=None,
        replace_ingredient=None,
    ):
        self.calls.append({
            "reason":
                reason,

            "preserve_meal_slots":
                list(
                    preserve_meal_slots
                    or []
                ),

            "replace_ingredient":
                replace_ingredient,
        })

        ingredients = []

        for ingredient in (
            self.previous_result
            .ingredients
        ):
            quantity = {
                "rice": 900.0,
                "lentils": 900.0,
            }.get(
                ingredient.id,
                ingredient.quantity,
            )

            ingredients.append(
                ingredient.model_copy(
                    update={
                        "quantity":
                            quantity
                    }
                )
            )

        return {
            "meals":
                previous_meals,

            "ingredients":
                ingredients,

            "nutrition_summary":
                self.previous_result
                .nutrition_summary,

            "warnings":
                [
                    "Fake reduce-cost replan."
                ],

            "source":
                "synthetic",
        }
class StaticMealReplanner:
    """
    Returns exactly the result provided by the test.

    Useful for testing invalid, unchanged,
    expensive or replacement meal replans.
    """

    def __init__(self, result):
        self.result = result
        self.calls = []

    def __call__(
        self,
        request,
        effective_context,
        previous_meals,
        reason,
        preserve_meal_slots=None,
        replace_ingredient=None,
    ):
        self.calls.append({
            "reason": reason,
            "preserve_meal_slots": list(
                preserve_meal_slots or []
            ),
            "replace_ingredient":
                replace_ingredient,
        })

        return self.result
    
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


def test_chat_reduce_cost_runs_meal_replan():

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

    meal_replanner = (
        FakeMealReplanner(
            previous_result
        )
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

        meal_replanner=meal_replanner,
    )

    result = planner.handle_chat_message(
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

    assert (
        previous_result.basket_total_minor
        == 49000
    )

    assert (
        result.basket_total_minor
        == 34000
    )

    assert (
        result.basket_total_minor
        <
        previous_result.basket_total_minor
    )

    assert (
        result.version
        ==
        previous_result.version + 1
    )

    assert len(
        meal_replanner.calls
    ) == 1

    assert (
        meal_replanner.calls[0][
            "reason"
        ]
        == "reduce_cost"
    )

    assert (
        meal_replanner.calls[0][
            "preserve_meal_slots"
        ]
        == ["breakfast"]
    )
def test_change_budget_decrease_runs_reduce_cost():

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

    meal_replanner = (
        FakeMealReplanner(
            previous_result
        )
    )

    planner = UlianaPlanner(
        catalog=catalog,

        chat_interpreter=(
            FakeChatInterpreter(
                ChatCommand(
                    intent="change_budget",
                    budget_uah=400,
                )
            )
        ),

        meal_replanner=(
            meal_replanner
        ),
    )

    result = planner.handle_chat_message(
        message="Зміни бюджет на 400 грн",

        previous_result=(
            previous_result
        ),

        session=object(),

        emit_progress=lambda *_: None,
    )

    # Budget really changed:
    # 1800 UAH -> 400 UAH.
    assert (
        result.budget_minor
        == 40000
    )

    assert (
        result.effective_request
        .budget_minor
        == 40000
    )

    # Our fake reduce-cost replan
    # produces the cheaper 340 UAH basket.
    assert (
        result.basket_total_minor
        == 34000
    )

    assert (
        result.basket_total_minor
        <= result.budget_minor
    )

    assert (
        result.budget_remaining_minor
        == 6000
    )

    assert (
        result.budget_status
        == "within_budget"
    )

    assert (
        result.version
        ==
        previous_result.version + 1
    )

    # Most important assertion:
    # change_budget selected reduce_cost.
    assert len(
        meal_replanner.calls
    ) == 1

    assert (
        meal_replanner.calls[0][
            "reason"
        ]
        == "reduce_cost"
    )
def test_change_budget_increase_runs_upgrade_plan():

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

    meal_replanner = (
        FakeMealReplanner(
            previous_result
        )
    )

    planner = UlianaPlanner(
        catalog=catalog,

        chat_interpreter=(
            FakeChatInterpreter(
                ChatCommand(
                    intent="change_budget",
                    budget_uah=2500,
                )
            )
        ),

        meal_replanner=(
            meal_replanner
        ),
    )

    result = planner.handle_chat_message(
        message="Бюджет тепер 2500 грн",

        previous_result=(
            previous_result
        ),

        session=object(),

        emit_progress=lambda *_: None,
    )

    # New budget must be preserved
    # through the upgrade flow.
    assert (
        result.budget_minor
        == 250000
    )

    assert (
        result.effective_request
        .budget_minor
        == 250000
    )

    assert (
        result.budget_status
        == "within_budget"
    )

    assert (
        result.basket_total_minor
        <= result.budget_minor
    )

    assert (
        result.budget_remaining_minor
        ==
        result.budget_minor
        - result.basket_total_minor
    )

    assert (
        result.version
        ==
        previous_result.version + 1
    )

    # Most important assertion:
    # change_budget selected upgrade_plan.
    assert len(
        meal_replanner.calls
    ) == 1

    assert (
        meal_replanner.calls[0][
            "reason"
        ]
        == "upgrade_plan"
    )
def test_chat_upgrade_plan():

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

    meal_replanner = (
        FakeMealReplanner(
            previous_result
        )
    )

    planner = UlianaPlanner(
        catalog=catalog,

        chat_interpreter=(
            FakeChatInterpreter(
                ChatCommand(
                    intent="upgrade_plan",

                    preserve_meal_slots=[
                        "breakfast"
                    ],
                )
            )
        ),

        meal_replanner=(
            meal_replanner
        ),
    )

    result = planner.handle_chat_message(
        message=(
            "Зроби меню різноманітнішим, "
            "але не змінюй сніданки"
        ),

        previous_result=(
            previous_result
        ),

        session=object(),

        emit_progress=lambda *_: None,
    )

    # Direct upgrade does NOT
    # change the user's budget.
    assert (
        result.budget_minor
        ==
        previous_result.budget_minor
    )

    assert (
        result.effective_request
        .budget_minor
        ==
        previous_result.effective_request
        .budget_minor
    )

    assert (
        result.budget_status
        == "within_budget"
    )

    assert (
        result.version
        ==
        previous_result.version + 1
    )

    assert len(
        meal_replanner.calls
    ) == 1

    assert (
        meal_replanner.calls[0][
            "reason"
        ]
        == "upgrade_plan"
    )

    assert (
        meal_replanner.calls[0][
            "preserve_meal_slots"
        ]
        == ["breakfast"]
    )
@pytest.mark.parametrize(
    "command",
    [
        ChatCommand(
            intent="reduce_cost"
        ),
        ChatCommand(
            intent="upgrade_plan"
        ),
        ChatCommand(
            intent="replace_ingredient",
            ingredient="rice",
        ),
        ChatCommand(
            intent="explain_plan"
        ),
    ],
)
def test_chat_modification_requires_existing_plan(
    command,
):
    planner = UlianaPlanner(
        catalog=DemoCatalog(),
        chat_interpreter=(
            FakeChatInterpreter(
                command
            )
        ),
    )

    response = (
        planner.handle_chat_message(
            message="Modify the plan",

            previous_result=None,

            session=object(),

            emit_progress=lambda *_: None,
        )
    )

    assert (
        response["type"]
        == "clarification"
    )

    assert (
        "create a plan"
        in response["message"].lower()
    )


def test_meal_replanner_rejects_none_result():

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
                    intent="reduce_cost"
                )
            )
        ),

        meal_replanner=(
            StaticMealReplanner(
                None
            )
        ),
    )

    with pytest.raises(
        ValueError,
        match="invalid result",
    ):
        planner.handle_chat_message(
            message="Зроби дешевше",

            previous_result=(
                previous_result
            ),

            session=object(),

            emit_progress=lambda *_: None,
        )


def test_meal_replanner_rejects_wrong_type():

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
                    intent="reduce_cost"
                )
            )
        ),

        meal_replanner=(
            StaticMealReplanner(
                []
            )
        ),
    )

    with pytest.raises(
        ValueError,
        match="invalid result",
    ):
        planner.handle_chat_message(
            message="Зроби дешевше",

            previous_result=(
                previous_result
            ),

            session=object(),

            emit_progress=lambda *_: None,
        )


def test_meal_replanner_rejects_missing_ingredients():

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

    invalid_meal_result = {
        "meals":
            previous_result.meal_plan,

        # "ingredients" intentionally missing

        "nutrition_summary":
            previous_result
            .nutrition_summary,

        "source":
            "synthetic",
    }

    planner = UlianaPlanner(
        catalog=catalog,

        chat_interpreter=(
            FakeChatInterpreter(
                ChatCommand(
                    intent="reduce_cost"
                )
            )
        ),

        meal_replanner=(
            StaticMealReplanner(
                invalid_meal_result
            )
        ),
    )

    with pytest.raises(
        ValueError,
        match="Missing fields: ingredients",
    ):
        planner.handle_chat_message(
            message="Зроби дешевше",

            previous_result=(
                previous_result
            ),

            session=object(),

            emit_progress=lambda *_: None,
        )


def test_reduce_cost_rejects_non_cheaper_replan():

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

    # Return exactly the same meals and ingredients.
    #
    # Therefore matching + optimizer should
    # produce exactly the same basket price.
    same_meal_result = {
        "meals":
            previous_result.meal_plan,

        "ingredients":
            previous_result.ingredients,

        "nutrition_summary":
            previous_result
            .nutrition_summary,

        "warnings": [],

        "source":
            "synthetic",
    }

    meal_replanner = (
        StaticMealReplanner(
            same_meal_result
        )
    )

    planner = UlianaPlanner(
        catalog=catalog,

        chat_interpreter=(
            FakeChatInterpreter(
                ChatCommand(
                    intent="reduce_cost"
                )
            )
        ),

        meal_replanner=(
            meal_replanner
        ),
    )

    response = (
        planner.handle_chat_message(
            message="Зроби дешевше",

            previous_result=(
                previous_result
            ),

            session=object(),

            emit_progress=lambda *_: None,
        )
    )

    assert (
        response["type"]
        == "no_cost_improvement"
    )

    assert (
        response[
            "previousBasketTotalMinor"
        ]
        == 49000
    )

    assert (
        response[
            "candidateBasketTotalMinor"
        ]
        == 49000
    )

    assert len(
        meal_replanner.calls
    ) == 1

    assert (
        meal_replanner.calls[0][
            "reason"
        ]
        == "reduce_cost"
    )


def test_upgrade_plan_rejects_plan_over_budget():

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

    # Make every ingredient extremely large.
    #
    # Demo catalog products still match,
    # but the final basket will exceed
    # the current 1800 UAH budget.
    expensive_ingredients = [
        ingredient.model_copy(
            update={
                "quantity":
                    10000.0
            }
        )
        for ingredient
        in previous_result.ingredients
    ]

    expensive_meal_result = {
        "meals":
            previous_result.meal_plan,

        "ingredients":
            expensive_ingredients,

        "nutrition_summary":
            previous_result
            .nutrition_summary,

        "warnings": [],

        "source":
            "synthetic",
    }

    meal_replanner = (
        StaticMealReplanner(
            expensive_meal_result
        )
    )

    planner = UlianaPlanner(
        catalog=catalog,

        chat_interpreter=(
            FakeChatInterpreter(
                ChatCommand(
                    intent="upgrade_plan"
                )
            )
        ),

        meal_replanner=(
            meal_replanner
        ),
    )

    response = (
        planner.handle_chat_message(
            message=(
                "Зроби меню кращим"
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
        == "upgrade_not_feasible"
    )

    assert (
        response[
            "budgetMinor"
        ]
        == 180000
    )

    assert (
        response[
            "candidateBasketTotalMinor"
        ]
        > response["budgetMinor"]
    )

    assert len(
        meal_replanner.calls
    ) == 1

    assert (
        meal_replanner.calls[0][
            "reason"
        ]
        == "upgrade_plan"
    )


def test_replace_ingredient_runs_real_replan():

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

    # Simulate Sofia successfully replacing rice.
    #
    # For this orchestration test we remove
    # the rice requirement from the returned
    # ingredient list.
    replacement_ingredients = [
        ingredient
        for ingredient
        in previous_result.ingredients
        if ingredient.id != "rice"
    ]

    replacement_meal_result = {
        "meals":
            previous_result.meal_plan,

        "ingredients":
            replacement_ingredients,

        "nutrition_summary":
            previous_result
            .nutrition_summary,

        "warnings":
            [
                "Fake ingredient replacement."
            ],

        "source":
            "synthetic",
    }

    meal_replanner = (
        StaticMealReplanner(
            replacement_meal_result
        )
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

        meal_replanner=(
            meal_replanner
        ),
    )

    result = (
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
        result.version
        ==
        previous_result.version + 1
    )

    assert all(
        ingredient.id != "rice"
        for ingredient
        in result.ingredients
    )

    assert all(
        ingredient.name
        != "Dry rice"
        for ingredient
        in result.ingredients
    )

    assert len(
        meal_replanner.calls
    ) == 1

    assert (
        meal_replanner.calls[0][
            "reason"
        ]
        == "replace_ingredient"
    )

    assert (
        meal_replanner.calls[0][
            "replace_ingredient"
        ]
        == "Dry rice"
    )
def test_replace_ingredient_rejects_unchanged_ingredient():

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

    # Replanner pretends that it completed
    # the replacement, but actually returns
    # exactly the same ingredients.
    unchanged_meal_result = {
        "meals":
            previous_result.meal_plan,

        "ingredients":
            previous_result.ingredients,

        "nutrition_summary":
            previous_result
            .nutrition_summary,

        "warnings": [],

        "source":
            "synthetic",
    }

    meal_replanner = (
        StaticMealReplanner(
            unchanged_meal_result
        )
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

        meal_replanner=(
            meal_replanner
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
        == "invalid_replan"
    )

    assert (
        response["ingredient"]
        == "Dry rice"
    )

    assert (
        response["ingredientId"]
        == "rice"
    )

    assert len(
        meal_replanner.calls
    ) == 1

    assert (
        meal_replanner.calls[0][
            "reason"
        ]
        == "replace_ingredient"
    )

    assert (
        meal_replanner.calls[0][
            "replace_ingredient"
        ]
        == "Dry rice"
    )