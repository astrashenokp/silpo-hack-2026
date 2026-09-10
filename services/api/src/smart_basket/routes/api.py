from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, Request, Response

from smart_basket.catalog.matching import line_total
from smart_basket.core import ApiError, Session, now, uid
from smart_basket.mcp.adapters import get_user_context, search_products
from smart_basket.mcp.connection import SessionTokenStorage, get_mcp_session
from smart_basket.meals import supported_labels
from smart_basket.schemas import (
    CartPreview, CartReceipt, Confirmation, ExportAccepted, FatSecretExport,
    FatSecretPreview, FatSecretPreviewRequest, FatSecretStatus, Health, PlanReference,
    PlanningRequest, PlanningResult, ProductSearchResponse, ProgressEvent, RecalculateRequest,
    RunSnapshot, SupportedLabels, UserContext,
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
        if result.data_mode not in {"demo", "mixed"} or result.effective_request != request:
            raise ValueError("Planner must retain the confirmed request and return a supported data mode.")
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


@router.get("/filters", response_model=SupportedLabels)
def filters():
    return SupportedLabels(**supported_labels())


@router.get("/context", response_model=UserContext)
async def context(request: Request, response: Response):
    with request.app.state.sessions_lock:
        id = request.cookies.get("smart_basket_demo")
        owner = request.app.state.sessions.get(id)
        if owner is None:
            owner = Session(uid("session"))
            request.app.state.sessions[owner.id] = owner
            response.set_cookie("smart_basket_demo", owner.id, httponly=True, samesite="lax", path="/")
    if not owner.silpo_connected:
        return request.app.state.catalog.get_user_context(owner)
    try:
        async with get_mcp_session(SessionTokenStorage(owner)) as mcp_session:
            live_context = await get_user_context(mcp_session, owner)
    except Exception as exc:
        message = str(exc).lower()
        if any(value in message for value in ("401", "403", "unauthorized", "invalid_token")):
            with owner.lock:
                owner.silpo_connected = False
            raise ApiError("AUTH_REQUIRED", "Reconnect the Silpo account.", 401) from exc
        if "429" in message or "rate limit" in message:
            raise ApiError("RATE_LIMITED", "Silpo request limit was reached.", 429, True) from exc
        raise ApiError("UPSTREAM_UNAVAILABLE", "Could not load context from Silpo.", 502, True) from exc
    response.headers["X-Data-Mode"] = "live"
    return live_context


@router.get("/integrations/silpo/products", response_model=ProductSearchResponse)
async def silpo_product_search(
    request: Request,
    response: Response,
    owner: SessionDependency,
    query: Annotated[str, Query(min_length=1, max_length=200)],
):
    with owner.lock:
        connected = owner.silpo_connected
        branch_id = owner.silpo_branch_id
        cart_id = owner.silpo_cart_id
        delivery_type = owner.silpo_delivery_type
        timeslot = owner.silpo_timeslot
        tool_schemas = dict(owner.silpo_tool_schemas)
    if not connected:
        raise ApiError("AUTH_REQUIRED", "Connect the Silpo account before searching products.", 401)
    if not branch_id:
        raise ApiError("CART_CONTEXT_REQUIRED", "Load Silpo context before searching products.", 409)
    try:
        async with get_mcp_session(SessionTokenStorage(owner)) as mcp_session:
            result = await search_products(
                mcp_session,
                query,
                branch_id,
                cart_id=cart_id,
                delivery_type=delivery_type,
                timeslot=timeslot,
                tool_schemas=tool_schemas,
            )
    except Exception as exc:
        message = str(exc).lower()
        if any(value in message for value in ("401", "403", "unauthorized", "invalid_token")):
            with owner.lock:
                owner.silpo_connected = False
            raise ApiError("AUTH_REQUIRED", "Reconnect the Silpo account.", 401) from exc
        if "429" in message or "rate limit" in message:
            raise ApiError("RATE_LIMITED", "Silpo request limit was reached.", 429, True) from exc
        raise ApiError("UPSTREAM_UNAVAILABLE", "Could not search Silpo products.", 502, True) from exc
    response.headers["X-Data-Mode"] = "live"
    return result


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
    with owner.lock:
        connected = owner.fatsecret_connected
        account_label = owner.fatsecret_account_label
    return FatSecretStatus(
        connected=connected,
        account_label=account_label if connected else None,
        export_available=True,
        reason=(
            "FatSecret account connected; Saved Meal exports are still simulated in demo mode."
            if connected
            else "DEMO: only simulated export is available; no real account is connected."
        ),
    )


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
