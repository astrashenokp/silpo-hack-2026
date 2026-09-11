"""Shared helpers for end-to-end checks against a running Smart Basket stack."""

import json
import os
import time
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
# Default to the Next.js origin so every check also exercises /api forwarding.
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:3000").rstrip("/")
POLL_TIMEOUT_SECONDS = float(os.getenv("E2E_POLL_TIMEOUT_SECONDS", "30"))


def load_fixture(name):
    return json.loads((REPO_ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def new_client():
    return httpx.Client(base_url=BASE_URL, timeout=15)


def start_session(client):
    """Mirror the browser: GET /api/context issues the demo session cookie."""
    response = client.get("/api/context")
    assert response.status_code == 200, response.text
    return response.json()


def line_total(quantity, unit_price_minor):
    """Contract rule: round(quantity * unitPriceMinor) half-up, in integer kopiykas."""
    exact = Decimal(str(quantity)) * unit_price_minor
    return int(exact.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"error"}, body
    error = body["error"]
    assert error["code"] == code, error
    assert isinstance(error["message"], str) and error["message"]
    assert isinstance(error["retryable"], bool)
    return error


def get_json(client, path):
    response = client.get(path)
    assert response.status_code == 200, response.text
    return response.json()


def _wait(fetch, is_terminal, label):
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    while True:
        body = fetch()
        if is_terminal(body):
            return body
        if time.monotonic() > deadline:
            raise AssertionError(f"{label} is not terminal after {POLL_TIMEOUT_SECONDS}s: {body}")
        time.sleep(0.25)


def poll_run(client, run_id):
    return _wait(lambda: get_json(client, f"/api/plans/{run_id}"),
                 lambda run: run["status"] in {"completed", "failed"}, f"Run {run_id}")


def start_plan(client, request, scenario=None):
    headers = {"X-Demo-Scenario": scenario} if scenario else {}
    response = client.post("/api/plans", json=request, headers=headers)
    assert response.status_code == 202, response.text
    queued = response.json()
    assert queued["status"] == "queued" and queued["result"] is None, queued
    return poll_run(client, queued["runId"])


def completed_result(client, request):
    run = start_plan(client, request)
    assert run["status"] == "completed", run
    assert run["stage"] == "ready", run
    return run["result"]


def plan_ref(result):
    return {"runId": result["runId"], "version": result["version"]}


def poll_export(client, export_id):
    return _wait(lambda: get_json(client, f"/api/fatsecret/exports/{export_id}"),
                 lambda export: export["status"] in {"success", "partial", "failed"},
                 f"Export {export_id}")
