"""Edamam Meal Planner adapter boundary.

The live request shape must be verified against the team's actual Edamam account
before enabling production use. This module keeps credentials and provider data
behind Sofiia's Python boundary and never stores raw recipe payloads as fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from urllib import error, request


class EdamamUnavailable(RuntimeError):
    """Raised when Edamam cannot be used for this run."""


@dataclass(frozen=True)
class EdamamSettings:
    app_id: str
    app_key: str
    account_user: str
    base_url: str = "https://api.edamam.com"
    timeout_seconds: float = 8.0

    @classmethod
    def from_env(cls) -> "EdamamSettings | None":
        app_id = os.getenv("EDAMAM_MEAL_PLANNER_APP_ID")
        app_key = os.getenv("EDAMAM_MEAL_PLANNER_APP_KEY")
        account_user = os.getenv("EDAMAM_ACCOUNT_USER")
        if not app_id or not app_key or not account_user:
            return None
        return cls(
            app_id=app_id,
            app_key=app_key,
            account_user=account_user,
            base_url=os.getenv("EDAMAM_MEAL_PLANNER_BASE_URL", "https://api.edamam.com"),
            timeout_seconds=float(os.getenv("EDAMAM_TIMEOUT_SECONDS", "8")),
        )


def build_edamam_payload(request_model, filters) -> dict:
    payload: dict = {
        "size": request_model.days,
        "plan": {
            "accept": {
                "all": [
                    {"health": list(filters.edamam_health_labels)},
                ],
            },
            "sections": {
                "Breakfast": {},
                "Lunch": {},
                "Dinner": {},
            },
        },
    }
    if request_model.calories_per_person_per_day is not None:
        payload["plan"]["fit"] = {
            "ENERC_KCAL": {
                "min": int(request_model.calories_per_person_per_day * 0.85),
                "max": int(request_model.calories_per_person_per_day * 1.15),
            }
        }
    return payload


class EdamamMealPlannerClient:
    def __init__(self, settings: EdamamSettings):
        self.settings = settings

    def request_plan(self, payload: dict) -> dict:
        url = (
            f"{self.settings.base_url.rstrip('/')}/api/meal-planner/v1/"
            f"{self.settings.account_user}/select"
            f"?app_id={self.settings.app_id}&app_key={self.settings.app_key}"
        )
        data = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.settings.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            if exc.code == 429:
                raise EdamamUnavailable("Edamam rate limit was reached.") from exc
            raise EdamamUnavailable(f"Edamam returned HTTP {exc.code}.") from exc
        except (TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise EdamamUnavailable("Edamam meal planner is unavailable or returned invalid data.") from exc
