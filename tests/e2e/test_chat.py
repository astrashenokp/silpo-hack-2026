"""The chat route: one natural-language change against the current plan."""

import os

import pytest

from stack import assert_error, completed_result, plan_ref

needs_no_key = pytest.mark.skipif(
    bool(os.getenv("GEMINI_API_KEY")),
    reason="A Gemini key is configured, so the interpreter answers for real.",
)


def test_chat_requires_a_session(anonymous):
    assert_error(anonymous.post("/api/chat", json={"message": "зроби дешевше"}), 401, "AUTH_REQUIRED")


def test_empty_message_is_rejected(client):
    assert_error(client.post("/api/chat", json={"message": ""}), 400, "VALIDATION_ERROR")


def test_chat_answers_in_the_contract_shape(client):
    response = client.post("/api/chat", json={"message": "зроби дешевше"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"type", "message", "run"}
    assert isinstance(body["type"], str)


@needs_no_key
def test_a_missing_interpreter_is_reported_not_crashed(client):
    body = client.post("/api/chat", json={"message": "зроби дешевше"}).json()
    assert body["type"] == "chat_error"
    assert body["run"] is None


@needs_no_key
def test_a_reply_without_a_new_plan_keeps_the_current_plan_confirmable(client, planning_request):
    result = completed_result(client, planning_request)
    body = client.post("/api/chat", json={**plan_ref(result), "message": "поясни план"}).json()
    assert body["type"] != "plan"
    # A chat that changes nothing must not supersede the plan the user already reviewed.
    preview = client.post("/api/cart/preview", json=plan_ref(result))
    assert preview.status_code == 200, preview.text
