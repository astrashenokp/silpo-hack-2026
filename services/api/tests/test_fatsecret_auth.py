from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from smart_basket.app import create_app
from smart_basket.fatsecret.auth import FatSecretOAuthManager, FatSecretSettings
from smart_basket.fatsecret.client import (
    ACCESS_TOKEN_URL,
    AUTHORIZE_URL,
    REQUEST_TOKEN_URL,
    REST_API_URL,
    FatSecretClient,
    OAuthCredentials,
    oauth_signature,
)


def session_owner(app, client):
    return app.state.sessions[client.cookies["smart_basket_demo"]]


def test_oauth_signature_matches_rfc_5849_example():
    parameters = {
        "file": "vacation.jpg",
        "size": "original",
        "oauth_consumer_key": "dpf43f3p2l4k3l03",
        "oauth_token": "nnch734d00sl2jdk",
        "oauth_nonce": "kllo9940pd9333jh",
        "oauth_timestamp": "1191242096",
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_version": "1.0",
    }
    assert oauth_signature(
        "GET",
        "http://photos.example.net/photos",
        parameters,
        "kd94hf93k423kf44",
        "pfkkdhi9sl3r4s00",
    ) == "tR3+Ty81lMeYAr/Fid0kMTYa/WM="


class FakeFatSecretOAuth:
    def __init__(self):
        self.pending = {}

    async def start(self, owner):
        self.pending[owner.id] = "request-one"
        return f"{AUTHORIZE_URL}?oauth_token=request-one"

    async def finish(self, owner, *, oauth_token, oauth_verifier):
        assert self.pending[owner.id] == oauth_token
        assert oauth_verifier == "verifier-one"
        with owner.lock:
            owner.fatsecret_connected = True
            owner.fatsecret_access_token = "private-access-token"
            owner.fatsecret_access_secret = "private-access-secret"
            owner.fatsecret_account_label = "Connected FatSecret account"

    async def cancel(self, owner):
        self.pending.pop(owner.id, None)

    def return_url(self, *, connected):
        assert connected is True
        return "http://localhost:3000?fatsecret=connected"


def test_fatsecret_routes_connect_account_without_exposing_tokens():
    oauth = FakeFatSecretOAuth()
    app = create_app(fatsecret_oauth=oauth)
    with TestClient(app) as client:
        client.get("/api/context")
        started = client.get("/api/auth/fatsecret/start", follow_redirects=False)
        assert started.status_code == 302
        assert started.headers["location"] == f"{AUTHORIZE_URL}?oauth_token=request-one"

        callback = client.get(
            "/api/auth/fatsecret/callback"
            "?oauth_token=request-one&oauth_verifier=verifier-one",
            follow_redirects=False,
        )
        assert callback.status_code == 303
        assert callback.headers["location"] == "http://localhost:3000?fatsecret=connected"
        status = client.get("/api/integrations/fatsecret").json()
        assert status == {
            "connected": True,
            "accountLabel": "Connected FatSecret account",
            "exportAvailable": True,
            "reason": (
                "FatSecret account connected; Saved Meal exports are still simulated in demo mode."
            ),
        }
        assert "private-access" not in str(status)

        with TestClient(app) as stranger:
            stranger.get("/api/context")
            assert stranger.get("/api/integrations/fatsecret").json()["connected"] is False


def test_fatsecret_callback_rejects_missing_values_and_clears_pending_flow():
    oauth = FakeFatSecretOAuth()
    app = create_app(fatsecret_oauth=oauth)
    with TestClient(app) as client:
        client.get("/api/context")
        client.get("/api/auth/fatsecret/start", follow_redirects=False)
        response = client.get(
            "/api/auth/fatsecret/callback?oauth_token=request-one",
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_OAUTH_CALLBACK"
        assert oauth.pending == {}


@pytest.mark.asyncio
async def test_manager_keeps_request_and_access_secrets_in_one_session():
    settings = FatSecretSettings(
        consumer_key="consumer",
        consumer_secret="shared",
        callback_url="http://localhost/callback",
        frontend_url="http://localhost:3000",
    )

    class FakeClient:
        def __init__(self, consumer_key, consumer_secret, *, timeout):
            assert (consumer_key, consumer_secret, timeout) == ("consumer", "shared", 10.0)

        async def request_token(self, callback_url):
            assert callback_url == settings.callback_url
            return OAuthCredentials("request-token", "request-secret")

        async def access_token(self, request_token, request_secret, verifier):
            assert (request_token, request_secret, verifier) == (
                "request-token",
                "request-secret",
                "verifier",
            )
            return OAuthCredentials("access-token", "access-secret")

        async def call(self, api_method, parameters, *, access_token, access_secret):
            assert api_method == "profile.get"
            assert parameters is None
            assert (access_token, access_secret) == ("access-token", "access-secret")
            return {"profile": {"height_measure": "Cm"}}

    manager = FatSecretOAuthManager(
        settings_factory=lambda: settings,
        client_factory=FakeClient,
    )
    app = create_app(fatsecret_oauth=manager)
    with TestClient(app) as client:
        client.get("/api/context")
        owner = session_owner(app, client)
        url = await manager.start(owner)
        assert parse_qs(urlsplit(url).query)["oauth_token"] == ["request-token"]
        assert owner.fatsecret_request_secret == "request-secret"
        await manager.finish(
            owner,
            oauth_token="request-token",
            oauth_verifier="verifier",
        )
        assert owner.fatsecret_request_token is None
        assert owner.fatsecret_request_secret is None
        assert owner.fatsecret_access_token == "access-token"
        assert owner.fatsecret_access_secret == "access-secret"
        assert await manager.delegated_call(owner, "profile.get") == {
            "profile": {"height_measure": "Cm"}
        }


@pytest.mark.asyncio
async def test_signed_transport_covers_token_endpoints_and_delegated_calls():
    requests = []

    class FakeResponse:
        status_code = 200

        def __init__(self, *, text="", json_data=None):
            self.text = text
            self._json_data = json_data

        def raise_for_status(self):
            return None

        def json(self):
            return self._json_data

    responses = [
        FakeResponse(
            text=(
                "oauth_token=request-token&oauth_token_secret=request-secret"
                "&oauth_callback_confirmed=true"
            )
        ),
        FakeResponse(text="oauth_token=access-token&oauth_token_secret=access-secret"),
        FakeResponse(json_data={"profile": {"height_measure": "Cm"}}),
    ]

    class FakeHttpClient:
        def __init__(self, *, timeout):
            assert timeout == 7

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def request(self, method, url, **kwargs):
            requests.append((method, url, kwargs))
            return responses.pop(0)

    client = FatSecretClient(
        "consumer",
        "shared",
        timeout=7,
        nonce_factory=lambda: "nonce",
        clock=lambda: 1_700_000_000,
        http_client_factory=FakeHttpClient,
    )
    request_credentials = await client.request_token("http://localhost/callback")
    assert request_credentials == OAuthCredentials("request-token", "request-secret")
    access_credentials = await client.access_token(
        request_credentials.token,
        request_credentials.secret,
        "verifier",
    )
    assert access_credentials == OAuthCredentials("access-token", "access-secret")
    result = await client.call(
        "profile.get",
        access_token=access_credentials.token,
        access_secret=access_credentials.secret,
    )
    assert result == {"profile": {"height_measure": "Cm"}}

    assert [request[1] for request in requests] == [
        REQUEST_TOKEN_URL,
        ACCESS_TOKEN_URL,
        REST_API_URL,
    ]
    assert all(
        "oauth_signature" in request[2].get("params", request[2].get("data", {}))
        for request in requests
    )
    assert requests[-1][2]["data"]["oauth_token"] == "access-token"
    assert requests[-1][2]["data"]["method"] == "profile.get"
