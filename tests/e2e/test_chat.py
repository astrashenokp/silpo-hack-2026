"""The chat route: one natural-language change against the current plan."""

from stack import assert_error, completed_result, plan_ref

# These run against whatever deployment E2E_BASE_URL points at, which may or may not have a
# working Gemini key — and the local environment says nothing about that. So assert what holds
# either way instead of skipping on a local variable.


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


def test_an_interpreter_failure_is_reported_not_crashed(client):
    """Without a plan to change, the answer must still be a well-formed reply, never a crash."""
    response = client.post("/api/chat", json={"message": "зроби дешевше"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["type"] != "plan", "there is no plan to replan yet"
    # An interpreter that is missing, rate-limited or briefly unreachable all answer the same way.
    if body["type"] == "chat_error":
        assert body["run"] is None


def test_a_reply_without_a_new_plan_keeps_the_current_plan_confirmable(client, planning_request):
    result = completed_result(client, planning_request)
    body = client.post("/api/chat", json={**plan_ref(result), "message": "поясни план"}).json()
    if body["type"] == "plan":
        # An explanation that replanned anyway is a different behaviour, checked elsewhere;
        # superseding the reviewed plan is then expected, so there is nothing to assert here.
        return
    # A chat that changes nothing must not supersede the plan the user already reviewed.
    preview = client.post("/api/cart/preview", json=plan_ref(result))
    assert preview.status_code == 200, preview.text
