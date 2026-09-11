from typing import Literal

from pydantic import BaseModel, Field


class ChatCommand(BaseModel):
    intent: Literal[
        "create_plan",
        "recalculate_plan",
        "reduce_cost",
        "upgrade_plan",
        "replace_ingredient",
        "change_budget",
        "explain_plan",
        "unknown",
    ]

    ingredient: str | None = None

    preserve_meal_slots: list[
        Literal["breakfast", "lunch", "dinner"]
    ] = Field(default_factory=list)

    budget_uah: int | None = None

    original_message: str = ""