"""Process-local demo state. Never use this store for live provider writes."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import RLock
from uuid import uuid4

from smart_basket.schemas import Error, RunSnapshot

DEMO_WARNING = "DEMO: synthetic data; no provider account, cart or Saved Meal is changed."


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def expires() -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()


def uid(prefix: str) -> str:
    return f"demo-{prefix}-{uuid4().hex}"


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 409, retryable: bool = False):
        self.status = status
        self.error = Error(code=code, message=message, retryable=retryable)


@dataclass
class Session:
    id: str
    lock: RLock = field(default_factory=RLock)
    runs: dict[str, RunSnapshot] = field(default_factory=dict)
    superseded: set[str] = field(default_factory=set)
    cart: dict[str, tuple[float, int]] = field(default_factory=lambda: {"demo-existing-soap": (1.0, 3500)})
    cart_previews: dict = field(default_factory=dict)
    cart_receipts: dict = field(default_factory=dict)
    cart_keys: dict = field(default_factory=dict)
    cart_applied_runs: set[str] = field(default_factory=set)
    export_previews: dict = field(default_factory=dict)
    exports: dict = field(default_factory=dict)
    export_keys: dict = field(default_factory=dict)
    export_operations: dict = field(default_factory=dict)
    saved_meals: dict = field(default_factory=dict)
    silpo_tokens: object | None = None
    silpo_client_info: object | None = None
    silpo_auth_flow: object | None = None
    silpo_connected: bool = False
    silpo_tools: tuple[str, ...] = ()
    silpo_tool_schemas: dict[str, dict] = field(default_factory=dict)
    silpo_cart_id: str | None = None
    silpo_branch_id: str | None = None
    silpo_delivery_type: str | None = None
    silpo_timeslot: object | None = None

    def get_run(self, run_id: str) -> RunSnapshot:
        if run_id not in self.runs:
            raise ApiError("NOT_FOUND", "Run not found in this session.", 404)
        return self.runs[run_id]

    def get_plan(self, run_id: str, version: int):
        run = self.get_run(run_id)
        if run_id in self.superseded or run.result is None or run.result.version != version:
            raise ApiError("STALE_PLAN", "Plan is unavailable or has changed. Review the current result.")
        return run.result


def require_fresh(preview):
    if datetime.fromisoformat(preview.expires_at) <= datetime.now(timezone.utc):
        raise ApiError("STALE_PLAN", "Preview expired. Create and review a new preview.")
