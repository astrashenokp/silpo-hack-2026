"""Preview, confirmed Saved Meal writes, read-back, and duplicate protection."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any, Mapping

from smart_basket.core import ApiError, DEMO_WARNING, expires, require_fresh, uid
from smart_basket.fatsecret.auth import FatSecretOAuthError
from smart_basket.fatsecret.client import FatSecretClientError
from smart_basket.fatsecret.matching import match_live_personal_portion, match_personal_portion
from smart_basket.schemas import Error, ExportMealOutcome, FatSecretExport, FatSecretPreview


@dataclass(frozen=True)
class PreviewRecord:
    preview: FatSecretPreview
    scenario: str
    live: bool
    connection_revision: int


def _objects(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _scalar(value: Any) -> Any:
    # FatSecret wraps some scalar fields as {"value": ...} in JSON responses (seen on
    # saved_meal_id from saved_meal.create); saved_meal_item.add and
    # saved_meal_item(s).get.v2 do the same for food_id/serving_id/number_of_units, which
    # _matches() must unwrap or every write-verification read-back fails.
    if isinstance(value, dict):
        return value.get("value")
    return value


def _value(payload: Mapping[str, Any], key: str) -> str:
    value = _scalar(payload.get(key))
    if value in (None, ""):
        raise FatSecretClientError(f"FatSecret response omitted {key}.")
    return str(value)


def _saved_meals(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    root = payload.get("saved_meals", {})
    return _objects(root.get("saved_meal") if isinstance(root, dict) else None)


def _saved_items(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    root = payload.get("saved_meal_items", {})
    return _objects(root.get("saved_meal_item") if isinstance(root, dict) else None)


def _marker(run_id: str, version: int, meal_id: str) -> str:
    digest = hashlib.sha256(f"{run_id}:{version}:{meal_id}".encode()).hexdigest()[:20]
    return f"[smart-basket:{digest}]"


def _matches(remote: Mapping[str, Any], desired: Any) -> bool:
    try:
        units_match = abs(float(_scalar(remote.get("number_of_units"))) - desired.number_of_units) <= max(
            0.001, abs(desired.number_of_units) * 1e-6,
        )
    except (TypeError, ValueError):
        return False
    return (
        str(_scalar(remote.get("food_id"))) == desired.food_id
        and str(_scalar(remote.get("serving_id"))) == desired.serving_id
        and units_match
    )


class FatSecretExportService:
    """Use live delegated APIs for connected sessions and labelled mocks otherwise."""

    def __init__(self, oauth: Any):
        self.oauth = oauth

    async def preview(self, request: Any, session: Any, scenario: str = "success") -> FatSecretPreview:
        with session.lock:
            plan = session.get_plan(request.run_id, request.version)
            meals = {meal.id: meal for meal in plan.meal_plan}
            connected = session.fatsecret_connected
            account_label = session.fatsecret_account_label
            connection_revision = session.fatsecret_connection_revision
        if len(set(request.meal_ids)) != len(request.meal_ids) or set(request.meal_ids) - meals.keys():
            raise ApiError("VALIDATION_ERROR", "Select unique meal IDs from this plan.", 400)
        selection_keys = [(selection.meal_id, selection.ingredient_id) for selection in request.selections]
        if len(set(selection_keys)) != len(selection_keys):
            raise ApiError("VALIDATION_ERROR", "Select each meal ingredient at most once.", 400)
        selected_ids = set(request.meal_ids)
        for selection in request.selections:
            meal = meals.get(selection.meal_id)
            ingredient_ids = {amount.ingredient_id for amount in meal.ingredient_amounts} if meal else set()
            if selection.meal_id not in selected_ids or selection.ingredient_id not in ingredient_ids:
                raise ApiError(
                    "VALIDATION_ERROR",
                    "FatSecret selections must identify ingredients in the selected meals.",
                    400,
                )

        if connected:
            if (
                any(meals[meal_id].source == "edamam" for meal_id in request.meal_ids)
                and os.getenv("FATSECRET_ALLOW_EDAMAM_EXPORT", "false").casefold() not in {"1", "true", "yes"}
            ):
                raise ApiError(
                    "EXPORT_PERMISSION_REQUIRED",
                    "Live Edamam-derived export is disabled until the team's data-use permission is verified.",
                    409,
                )
            async def call(method: str, parameters: Mapping[str, object] | None = None):
                return await self.oauth.delegated_call(session, method, parameters)

            try:
                matched = []
                for meal_id in request.meal_ids:
                    overrides = {
                        selection.ingredient_id: (selection.food_id, selection.serving_id)
                        for selection in request.selections
                        if selection.meal_id == meal_id
                    }
                    matched.append(await match_live_personal_portion(
                        meals[meal_id], call, overrides,
                    ))
            except FatSecretOAuthError as exc:
                raise ApiError("AUTH_REQUIRED", str(exc), 401) from exc
            except FatSecretClientError as exc:
                if exc.provider_code == 9:
                    raise ApiError("AUTH_REQUIRED", "Reconnect the expired FatSecret account.", 401) from exc
                raise ApiError("UPSTREAM_UNAVAILABLE", str(exc), 502, True) from exc
            warnings = [
                "Review every FatSecret food and serving match before confirming.",
                "Saved Meals represent one personal portion and do not create diary entries.",
            ]
            if any(meal.unresolved for meal in matched):
                warnings.append(
                    "Unmatched ingredients will be skipped; each saved meal contains only the "
                    "reviewed FatSecret matches shown above."
                )
            live = True
        else:
            matched = [match_personal_portion(meals[meal_id], force_unmatched=scenario == "unmatched")
                       for meal_id in request.meal_ids]
            warnings = [DEMO_WARNING, "Nutrition comparison is unavailable in demo mode.",
                        f"Simulated export outcome: {scenario}."]
            account_label = "Demo account (no FatSecret connection)"
            live = False

        preview = FatSecretPreview(
            preview_id=uid("export-preview"),
            run_id=plan.run_id,
            version=plan.version,
            account_label=account_label or "Connected FatSecret account",
            expires_at=expires(),
            # A partially matched recipe is still useful and mirrors the reviewed-partial Silpo
            # basket flow. Never create an empty Saved Meal: every selected meal must retain at
            # least one verified food/serving match.
            can_confirm=all(meal.items for meal in matched),
            meals=matched,
            warnings=warnings,
        )
        with session.lock:
            session.export_previews[preview.preview_id] = PreviewRecord(
                preview, scenario, live, connection_revision,
            )
        return preview

    def confirm(self, request: Any, session: Any) -> tuple[str, bool]:
        with session.lock:
            record = session.export_previews.get(request.preview_id)
            if record is None:
                raise ApiError("NOT_FOUND", "Export preview not found in this session.", 404)
            prior = session.export_keys.get(request.idempotency_key)
            if prior:
                if prior[0] != request.preview_id:
                    raise ApiError("IDEMPOTENCY_CONFLICT", "This key belongs to another export preview.")
                return prior[1], False
            preview = record.preview
            require_fresh(preview)
            session.get_plan(preview.run_id, preview.version)
            if record.connection_revision != session.fatsecret_connection_revision or (
                record.live and not session.fatsecret_connected
            ):
                raise ApiError("STALE_ACCOUNT", "FatSecret connection changed. Create and review a new preview.")
            if not preview.can_confirm:
                raise ApiError(
                    "UNRESOLVED_FOODS",
                    "Each selected meal needs at least one matched FatSecret ingredient.",
                )

            identity = (
                "live" if record.live else "demo",
                record.connection_revision,
                preview.run_id,
                preview.version,
                tuple(sorted(
                    (
                        meal.meal_id,
                        tuple(sorted(
                            (item.ingredient_id, item.food_id, item.serving_id)
                            for item in meal.items
                        )),
                    )
                    for meal in preview.meals
                )),
            )
            existing_id = session.export_operations.get(identity)
            if existing_id:
                existing = session.exports[existing_id]
                should_retry = record.live and existing.status in {"partial", "failed"}
                session.export_operations[request.preview_id] = existing_id
                session.export_keys[request.idempotency_key] = (request.preview_id, existing_id)
                return existing_id, should_retry

            export_id = uid("export")
            message = "Queued for FatSecret saving." if record.live else "Queued for simulated saving."
            session.exports[export_id] = FatSecretExport(
                export_id=export_id,
                status="queued",
                meals=[ExportMealOutcome(
                    meal_id=meal.meal_id,
                    status="pending",
                    saved_meal_id=None,
                    message=message,
                ) for meal in preview.meals],
                error=None,
                warnings=[] if record.live else [DEMO_WARNING],
            )
            session.export_operations[identity] = export_id
            session.export_operations[request.preview_id] = export_id
            session.export_keys[request.idempotency_key] = (request.preview_id, export_id)
            return export_id, True

    async def execute(self, export_id: str, preview_id: str, session: Any) -> None:
        with session.lock:
            record = session.export_previews[preview_id]
            operation = session.exports[export_id]
            operation.status = "running"
            operation.error = None
            for outcome in operation.meals:
                outcome.status = "pending"
                outcome.message = "Saving and verifying with FatSecret." if record.live else outcome.message
        if not record.live:
            self._execute_demo(operation, record, session)
            return
        await self._execute_live(operation, record, session)

    def _execute_demo(self, operation: FatSecretExport, record: PreviewRecord, session: Any) -> None:
        preview, scenario = record.preview, record.scenario
        with session.lock:
            try:
                session.get_plan(preview.run_id, preview.version)
                for index, meal in enumerate(operation.meals):
                    identity = (
                        "demo", record.connection_revision,
                        preview.run_id, preview.version, meal.meal_id,
                    )
                    if identity in session.saved_meals:
                        meal.status = "already_saved"
                        meal.saved_meal_id = session.saved_meals[identity]
                        meal.message = "Previously saved demo meal reused."
                    elif scenario == "success" or (scenario == "partial" and index == 0):
                        session.saved_meals[identity] = uid("saved-meal")
                        meal.saved_meal_id = session.saved_meals[identity]
                        meal.status = "saved"
                        meal.message = "Demo Saved Meal recorded; no provider call made."
                    else:
                        meal.status = "failed"
                        meal.message = "Simulated provider failure; meal was not saved."
                self._finish(operation, retryable=False)
            except Exception:
                self._fail_remaining(operation, "Export stopped before this meal was saved.")

    async def _execute_live(self, operation: FatSecretExport, record: PreviewRecord, session: Any) -> None:
        preview = record.preview
        operation.warnings = []

        async def call(method: str, parameters: Mapping[str, object] | None = None):
            return await self.oauth.delegated_call(session, method, parameters)

        try:
            session.get_plan(preview.run_id, preview.version)
            with session.lock:
                if record.connection_revision != session.fatsecret_connection_revision:
                    raise ApiError("STALE_ACCOUNT", "FatSecret connection changed during export.")
            for preview_meal, outcome in zip(preview.meals, operation.meals, strict=True):
                identity = (
                    "live", record.connection_revision,
                    preview.run_id, preview.version, preview_meal.meal_id,
                )
                marker = _marker(preview.run_id, preview.version, preview_meal.meal_id)
                saved_meal_id = await self._find_saved_meal(call, marker)
                existed = saved_meal_id is not None
                if saved_meal_id is None:
                    try:
                        created = await call("saved_meal.create", {
                            "saved_meal_name": preview_meal.title,
                            "saved_meal_description": f"{marker} One personal portion from Smart Basket.",
                            "meals": "Other",
                        })
                        saved_meal_id = _value(created, "saved_meal_id")
                    except Exception:
                        saved_meal_id = await self._find_saved_meal(call, marker)
                        if saved_meal_id is None:
                            raise
                outcome.saved_meal_id = saved_meal_id
                with session.lock:
                    session.saved_meals[identity] = saved_meal_id

                before = await self._read_items(call, saved_meal_id)
                missing = [item for item in preview_meal.items if not any(_matches(remote, item) for remote in before)]
                write_failed = False
                for item in missing:
                    try:
                        await call("saved_meal_item.add", {
                            "saved_meal_id": saved_meal_id,
                            "food_id": item.food_id,
                            "saved_meal_item_name": item.matched_name,
                            "serving_id": item.serving_id,
                            "number_of_units": format(item.number_of_units, ".8g"),
                        })
                    except Exception:
                        reconciled = await self._read_items(call, saved_meal_id)
                        if not any(_matches(remote, item) for remote in reconciled):
                            write_failed = True

                verified = await self._read_items(call, saved_meal_id)
                complete = all(any(_matches(remote, item) for remote in verified) for item in preview_meal.items)
                if complete:
                    outcome.status = "already_saved" if existed and not missing else "saved"
                    skipped = len(preview_meal.unresolved)
                    outcome.message = (
                        "Saved Meal and all matched items verified by FatSecret read-back."
                        if not skipped
                        else (
                            "Saved Meal and all matched items verified by FatSecret read-back; "
                            f"{skipped} unmatched ingredient(s) were skipped."
                        )
                    )
                    if skipped:
                        operation.warnings.append(
                            f"{preview_meal.title}: skipped {skipped} unmatched ingredient(s)."
                        )
                else:
                    outcome.status = "partial" if saved_meal_id else "failed"
                    outcome.message = "Saved Meal exists, but one or more items could not be verified."
                    write_failed = True
                if write_failed:
                    operation.error = Error(
                        code="UPSTREAM_UNAVAILABLE",
                        message="One or more FatSecret writes could not be verified.",
                        retryable=True,
                    )
            self._finish(operation, retryable=True)
        except FatSecretOAuthError as exc:
            self._fail_remaining(operation, str(exc), code="AUTH_REQUIRED", retryable=False)
        except FatSecretClientError as exc:
            code = "AUTH_REQUIRED" if exc.provider_code == 9 else "UPSTREAM_UNAVAILABLE"
            self._fail_remaining(operation, str(exc), code=code, retryable=code != "AUTH_REQUIRED")
        except ApiError as exc:
            self._fail_remaining(operation, exc.error.message, code=exc.error.code, retryable=exc.error.retryable)
        except Exception:
            self._fail_remaining(operation, "FatSecret export failed unexpectedly.", retryable=True)

    async def _find_saved_meal(self, call: Any, marker: str) -> str | None:
        payload = await call("saved_meals.get.v2")
        for meal in _saved_meals(payload):
            if marker in str(meal.get("saved_meal_description", "")):
                return str(meal.get("saved_meal_id"))
        return None

    async def _read_items(self, call: Any, saved_meal_id: str) -> list[dict[str, Any]]:
        payload = await call("saved_meal_items.get.v2", {"saved_meal_id": saved_meal_id})
        return _saved_items(payload)

    @staticmethod
    def _finish(operation: FatSecretExport, *, retryable: bool) -> None:
        successes = sum(meal.status in {"saved", "already_saved"} for meal in operation.meals)
        has_partial = any(meal.status == "partial" for meal in operation.meals)
        operation.status = (
            "success" if successes == len(operation.meals)
            else "partial" if successes or has_partial
            else "failed"
        )
        if operation.status != "success" and operation.error is None:
            operation.error = Error(
                code="UPSTREAM_UNAVAILABLE",
                message="Some FatSecret meals were not saved and verified.",
                retryable=retryable,
            )

    @staticmethod
    def _fail_remaining(
        operation: FatSecretExport,
        message: str,
        *,
        code: str = "EXPORT_FAILED",
        retryable: bool = False,
    ) -> None:
        operation.status = "partial" if any(
            meal.status in {"saved", "already_saved", "partial"} for meal in operation.meals
        ) else "failed"
        operation.error = Error(code=code, message=message, retryable=retryable)
        for meal in operation.meals:
            if meal.status == "pending":
                meal.status = "failed"
                meal.message = "Export stopped before this meal was verified."


# Backwards-compatible name for imports outside the application factory.
DemoExportService = FatSecretExportService
