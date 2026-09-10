"""Browser-facing routes for connecting provider accounts."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from smart_basket.core import ApiError
from smart_basket.fatsecret.auth import FatSecretOAuthError
from smart_basket.fatsecret.client import FatSecretClientError
from smart_basket.mcp.oauth import SilpoOAuthError
from smart_basket.routes.api import SessionDependency
from smart_basket.schemas import SilpoStatus

router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/auth/silpo/start", response_class=RedirectResponse)
async def silpo_oauth_start(request: Request, owner: SessionDependency):
    try:
        authorization_url = await request.app.state.silpo_oauth.start(owner)
    except Exception as exc:
        raise ApiError("SILPO_AUTH_UNAVAILABLE", "Could not start Silpo authorization.", 503, True) from exc
    return RedirectResponse(authorization_url, status_code=302)


@router.get("/auth/silpo/callback", response_class=RedirectResponse)
async def silpo_oauth_callback(
    request: Request,
    owner: SessionDependency,
    code: str | None = None,
    state: str | None = None,
    iss: str | None = None,
    error: str | None = Query(default=None),
):
    manager = request.app.state.silpo_oauth
    if error:
        await manager.cancel(owner)
        raise ApiError("SILPO_AUTH_DENIED", "Silpo authorization was cancelled or denied.", 401)
    if not code or not state:
        await manager.cancel(owner)
        raise ApiError("INVALID_OAUTH_CALLBACK", "Silpo callback is missing code or state.", 400)
    try:
        await manager.finish(owner, code=code, state=state, iss=iss)
    except SilpoOAuthError as exc:
        raise ApiError("SILPO_AUTH_FAILED", str(exc), 401) from exc
    except Exception as exc:
        raise ApiError("SILPO_AUTH_FAILED", "Could not complete Silpo authorization.", 502, True) from exc
    return RedirectResponse(manager.return_url(connected=True), status_code=303)


@router.get("/integrations/silpo", response_model=SilpoStatus)
def silpo_status(owner: SessionDependency):
    with owner.lock:
        return SilpoStatus(
            connected=owner.silpo_connected,
            tools_available=list(owner.silpo_tools),
            reason=None if owner.silpo_connected else "Silpo account is not connected.",
        )


@router.get("/auth/fatsecret/start", response_class=RedirectResponse)
async def fatsecret_oauth_start(request: Request, owner: SessionDependency):
    try:
        authorization_url = await request.app.state.fatsecret_oauth.start(owner)
    except FatSecretOAuthError as exc:
        raise ApiError("FATSECRET_AUTH_UNAVAILABLE", str(exc), 503) from exc
    except FatSecretClientError as exc:
        raise ApiError(
            "FATSECRET_AUTH_UNAVAILABLE",
            str(exc),
            502 if exc.status_code is None or exc.status_code >= 500 else 401,
            exc.status_code is None or exc.status_code >= 500,
        ) from exc
    except Exception as exc:
        raise ApiError(
            "FATSECRET_AUTH_UNAVAILABLE",
            "Could not start FatSecret authorization.",
            502,
            True,
        ) from exc
    return RedirectResponse(authorization_url, status_code=302)


@router.get("/auth/fatsecret/callback", response_class=RedirectResponse)
async def fatsecret_oauth_callback(
    request: Request,
    owner: SessionDependency,
    oauth_token: str | None = None,
    oauth_verifier: str | None = None,
    denied: str | None = Query(default=None),
):
    manager = request.app.state.fatsecret_oauth
    if denied:
        await manager.cancel(owner)
        raise ApiError(
            "FATSECRET_AUTH_DENIED",
            "FatSecret authorization was cancelled or denied.",
            401,
        )
    if not oauth_token or not oauth_verifier:
        await manager.cancel(owner)
        raise ApiError(
            "INVALID_OAUTH_CALLBACK",
            "FatSecret callback is missing oauth_token or oauth_verifier.",
            400,
        )
    try:
        await manager.finish(
            owner,
            oauth_token=oauth_token,
            oauth_verifier=oauth_verifier,
        )
    except FatSecretOAuthError as exc:
        raise ApiError("FATSECRET_AUTH_FAILED", str(exc), 401) from exc
    except FatSecretClientError as exc:
        raise ApiError(
            "FATSECRET_AUTH_FAILED",
            str(exc),
            502 if exc.status_code is None or exc.status_code >= 500 else 401,
            exc.status_code is None or exc.status_code >= 500,
        ) from exc
    except Exception as exc:
        raise ApiError(
            "FATSECRET_AUTH_FAILED",
            "Could not complete FatSecret authorization.",
            502,
            True,
        ) from exc
    return RedirectResponse(manager.return_url(connected=True), status_code=303)
