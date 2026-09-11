import httpx
import pytest

from stack import BASE_URL, load_fixture, new_client, start_session


def pytest_report_header(config):
    return f"e2e target: {BASE_URL}"


@pytest.fixture(scope="session", autouse=True)
def stack_is_up():
    try:
        response = httpx.get(f"{BASE_URL}/api/health", timeout=5)
    except httpx.HTTPError as exc:
        pytest.exit(f"No stack at {BASE_URL} ({exc}). Start it first: tests/e2e/README.md", returncode=2)
    if response.status_code != 200:
        pytest.exit(f"{BASE_URL}/api/health returned {response.status_code}: {response.text}", returncode=2)


@pytest.fixture
def planning_request():
    return load_fixture("planning-request.json")


@pytest.fixture
def anonymous():
    """A client without a demo session cookie."""
    with new_client() as client:
        yield client


@pytest.fixture
def client():
    """A browser-like client holding its own demo session."""
    with new_client() as client:
        start_session(client)
        yield client
