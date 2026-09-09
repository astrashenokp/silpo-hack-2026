"""Run with: python -m uvicorn smart_basket.app:app --host 127.0.0.1 --port 8000"""

import os
from threading import RLock

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from smart_basket.cart.service import DemoCartService
from smart_basket.core import ApiError
from smart_basket.demo import DemoCatalog
from smart_basket.agent import UlianaPlanner
from smart_basket.fatsecret.export import DemoExportService
from smart_basket.routes.api import router
from smart_basket.schemas import ErrorEnvelope


def create_app(*, planner=None, catalog=None):
    if os.getenv("SMART_BASKET_MODE", "demo") != "demo":
        raise RuntimeError("Only demo mode is implemented. Live adapters and durable storage are required first.")
    app = FastAPI(title="Smart Basket API (demo)", version="0.2.0",
                  description="Synthetic fixtures only. GET /api/context initializes a demo cookie session.",
                  responses={code: {"model": ErrorEnvelope} for code in (400, 401, 404, 409, 429, 500, 502, 503)})
    app.state.sessions = {}
    app.state.sessions_lock = RLock()
    app.state.catalog = catalog if catalog is not None else DemoCatalog()
    app.state.planner = planner if planner is not None else UlianaPlanner(app.state.catalog)
    app.state.cart_service = DemoCartService(app.state.catalog)
    app.state.export_service = DemoExportService()
    origins = [s.strip() for s in os.getenv("SMART_BASKET_CORS_ORIGINS", "http://localhost:3000").split(",") if s.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Demo-Scenario"])

    @app.middleware("http")
    async def demo_response_headers(request: Request, call_next):
        # Cookie-authenticated mutations must originate from an explicitly allowed browser origin.
        origin = request.headers.get("origin")
        if request.method == "POST" and origin and origin not in origins:
            return JSONResponse(status_code=403, content={"error": {"code": "ORIGIN_NOT_ALLOWED",
                "message": "Browser origin is not allowed.", "retryable": False}})
        response = await call_next(request)
        response.headers["X-Data-Mode"] = "demo"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ApiError)
    async def api_error(request, exc):
        return JSONResponse(status_code=exc.status, content={"error": exc.error.model_dump()})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        descriptions = [f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in exc.errors()]
        return JSONResponse(status_code=400, content={"error": {"code": "VALIDATION_ERROR",
            "message": "; ".join(descriptions), "retryable": False}})

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"error": {
            "code": "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR",
            "message": str(exc.detail), "retryable": False}})

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR",
            "message": "Unexpected server error.", "retryable": False}})

    app.include_router(router)
    # FastAPI's default validation response is 422; this contract deliberately returns 400.
    original_openapi = app.openapi

    def openapi():
        schema = original_openapi()
        for path in schema["paths"].values():
            for operation in path.values():
                operation.get("responses", {}).pop("422", None)
        return schema

    app.openapi = openapi
    return app


app = create_app()
