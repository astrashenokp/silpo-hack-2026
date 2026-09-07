from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request, Response

from smart_basket.catalog.matching import line_total
from smart_basket.core import ApiError, Session, now, uid
from smart_basket.schemas import (
    CartPreview, CartReceipt, Confirmation, ExportAccepted, FatSecretExport,
    FatSecretPreview, FatSecretPreviewRequest, FatSecretStatus, Health, PlanReference,
    PlanningRequest, PlanningResult, ProgressEvent, RecalculateRequest, RunSnapshot, UserContext,
)

router = APIRouter(prefix="/api")


def session(request: Request) -> Session:
    id = request.cookies.get("smart_basket_demo")
    with request.app.state.sessions_lock:
        found = request.app.state.sessions.get(id)
    if found is None:
        raise ApiError("AUTH_REQUIRED", "Initialize a demo session with GET /api/context.", 401)
    return found


SessionDependency = Annotated[Session, Depends(session)]
Scenario = Annotated[str, Header(alias="X-Demo-Scenario")]


def scenario(value: str, allowed: set[str]):
    if value not in allowed:
        raise ApiError("VALIDATION_ERROR", f"Supported demo scenarios: {', '.join(sorted(allowed))}.", 400)
    return value


def work(app, owner, run_id, request, previous=None, selected_ids=None, fail=False):
    with owner.lock:
        owner.runs[run_id].status = "running"

    def emit_progress(stage, message):
        event = ProgressEvent(stage=stage, message=message, at=now())
        with owner.lock:
            run = owner.runs[run_id]
            run.stage = event.stage
            run.events.append(event)

    try:
        if fail:
            raise ApiError("UPSTREAM_UNAVAILABLE", "Simulated planner failure.", 502, True)
        if previous is None:
            result = app.state.planner.run_planner(request, owner, emit_progress)
        else:
            result = app.state.planner.recalculate_plan(previous, selected_ids, owner, emit_progress)
        result = PlanningResult.model_validate(result).model_copy(deep=True)
        result.run_id = run_id
        result.version = previous.version + 1 if previous else 1
        if result.data_mode != "demo" or result.effective_request != request:
            raise ValueError("Mock service requires a demo result retaining the confirmed request.")
        if result.basket_total_minor != sum(p.line_total_minor for p in result.selected_products):
            raise ValueError("Planner returned inconsistent totals.")
        if any(p.line_total_minor != line_total(p.quantity, p.unit_price_minor) for p in result.selected_products):
            raise ValueError("Planner returned inconsistent line totals.")
        if (result.budget_minor != request.budget_minor or
                result.budget_remaining_minor != request.budget_minor - result.basket_total_minor):
            raise ValueError("Planner returned inconsistent budget fields.")
        with owner.lock:
            owner.runs[run_id].result = result
            owner.runs[run_id].status = "completed"
            emit_progress("ready", "Demo planning result is ready.")
    except Exception as exc:
        with owner.lock:
            run = owner.runs[run_id]
            run.status = "failed"
            run.error = exc.error if isinstance(exc, ApiError) else ApiError(
                "PLANNER_FAILED", "Planner could not produce a valid result.", 502, True).error


def queue_plan(request, tasks, app, owner, *, previous=None, selected_ids=None, fail=False):
    run_id = uid("run")
    initial = RunSnapshot(run_id=run_id, status="queued", stage="context", events=[], result=None, error=None)
    with owner.lock:
        owner.runs[run_id] = initial.model_copy(deep=True)
    tasks.add_task(work, app, owner, run_id, request, previous, selected_ids, fail)
    return initial


@router.get("/health", response_model=Health)
def health():
    return Health()


@router.get("/context", response_model=UserContext)
def context(request: Request, response: Response):
    with request.app.state.sessions_lock:
        id = request.cookies.get("smart_basket_demo")
        owner = request.app.state.sessions.get(id)
        if owner is None:
            owner = Session(uid("session"))
            request.app.state.sessions[owner.id] = owner
            response.set_cookie("smart_basket_demo", owner.id, httponly=True, samesite="lax", path="/")
    return request.app.state.catalog.get_user_context(owner)


@router.post("/plans", status_code=202, response_model=RunSnapshot)
def create_plan(body: PlanningRequest, tasks: BackgroundTasks, request: Request,
                owner: SessionDependency, x_demo_scenario: Scenario = "success"):
    scenario(x_demo_scenario, {"success", "failed"})
    return queue_plan(body, tasks, request.app, owner, fail=x_demo_scenario == "failed")


@router.get("/plans/{run_id}", response_model=RunSnapshot)
def get_plan(run_id: str, owner: SessionDependency):
    with owner.lock:
        return owner.get_run(run_id).model_copy(deep=True)


@router.post("/plans/{run_id}/recalculate", status_code=202, response_model=RunSnapshot)
def recalculate(run_id: str, body: RecalculateRequest, tasks: BackgroundTasks,
                request: Request, owner: SessionDependency):
    with owner.lock:
        previous = owner.get_plan(run_id, body.version).model_copy(deep=True)
        known = {item.id for item in previous.recurring_items}
        if set(body.selected_recurring_ids) - known or len(set(body.selected_recurring_ids)) != len(body.selected_recurring_ids):
            raise ApiError("VALIDATION_ERROR", "Select unique recurring IDs from this result.", 400)
        initial = queue_plan(previous.effective_request, tasks, request.app, owner,
                             previous=previous, selected_ids=body.selected_recurring_ids)
        owner.superseded.add(run_id)
        return initial


@router.post("/cart/preview", response_model=CartPreview)
def cart_preview(body: PlanReference, request: Request, owner: SessionDependency,
                 x_demo_scenario: Scenario = "success"):
    scenario(x_demo_scenario, {"success", "partial", "failed"})
    return request.app.state.cart_service.preview_cart(body.run_id, body.version, owner, x_demo_scenario)


@router.post("/cart/confirm", response_model=CartReceipt)
def cart_confirm(body: Confirmation, request: Request, owner: SessionDependency):
    return request.app.state.cart_service.confirm_cart(body.preview_id, body.idempotency_key, owner)


@router.get("/integrations/fatsecret", response_model=FatSecretStatus)
def fatsecret_status(owner: SessionDependency):
    return FatSecretStatus(connected=False, account_label="Demo account (no FatSecret connection)",
        export_available=True, reason="DEMO: only simulated export is available; no real account is connected.")


@router.post("/fatsecret/exports/preview", response_model=FatSecretPreview)
def export_preview(body: FatSecretPreviewRequest, request: Request, owner: SessionDependency,
                   x_demo_scenario: Scenario = "success"):
    scenario(x_demo_scenario, {"success", "partial", "failed", "unmatched"})
    return request.app.state.export_service.preview(body, owner, x_demo_scenario)


@router.post("/fatsecret/exports/confirm", status_code=202, response_model=ExportAccepted)
def export_confirm(body: Confirmation, tasks: BackgroundTasks, request: Request, owner: SessionDependency):
    export_id, is_new = request.app.state.export_service.confirm(body, owner)
    if is_new:
        tasks.add_task(request.app.state.export_service.execute, export_id, body.preview_id, owner)
    return ExportAccepted(export_id=export_id)


@router.get("/fatsecret/exports/{export_id}", response_model=FatSecretExport)
def get_export(export_id: str, owner: SessionDependency):
    with owner.lock:
        if export_id not in owner.exports:
            raise ApiError("NOT_FOUND", "Export not found in this session.", 404)
        return owner.exports[export_id].model_copy(deep=True)


@router.get("/auth/{provider}/{action}")
def unavailable_auth(provider: str, action: str):
    if provider not in {"silpo", "fatsecret"} or action not in {"start", "callback"}:
        raise ApiError("NOT_FOUND", "Route not found.", 404)
    raise ApiError("INTEGRATION_UNAVAILABLE", "OAuth awaits Arina's adapter. Use /api/context for demo mode.", 503)
