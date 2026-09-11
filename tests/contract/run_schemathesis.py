"""Contract fuzzing of the demo API with Schemathesis (owner: Polina).

Opens one demo session (GET /api/context), then runs `schemathesis run` against
packages/contracts/openapi.json with that session cookie. Provider sign-in routes and
the live Silpo search are excluded, so fuzzing never reaches a real provider.

Usage (repository root, QA virtual environment, backend running):
    & tests/.venv/Scripts/python.exe tests/contract/run_schemathesis.py [schemathesis options]

CONTRACT_BASE_URL selects the API (default http://127.0.0.1:8000). Extra arguments are
passed to `schemathesis run`, e.g. `--max-examples 20` or `--checks not_a_server_error`.
"""

import os
import subprocess
import sys
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
SCHEMA = HERE.parents[1] / "packages" / "contracts" / "openapi.json"
BASE_URL = os.getenv("CONTRACT_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
EXCLUDED_PATHS = r"^/api/(auth/|integrations/silpo/)"


def demo_session_cookie():
    with urlopen(f"{BASE_URL}/api/context", timeout=10) as response:
        for header in response.headers.get_all("Set-Cookie") or []:
            cookie = SimpleCookie(header)
            if "smart_basket_demo" in cookie:
                return cookie["smart_basket_demo"].value
    raise SystemExit(f"{BASE_URL}/api/context did not issue a demo session cookie.")


def main():
    executable = Path(sys.executable).with_name("schemathesis.exe" if os.name == "nt" else "schemathesis")
    command = [
        str(executable), "run", str(SCHEMA),
        "--url", BASE_URL,
        "--header", f"Cookie: smart_basket_demo={demo_session_cookie()}",
        "--exclude-path-regex", EXCLUDED_PATHS,
        "--report", "junit",
        "--report-dir", str(HERE / "reports"),
        *sys.argv[1:],
    ]
    # UTF-8 output: Schemathesis prints box-drawing characters that a cp1251 Windows console rejects.
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    # Running inside tests/contract keeps Hypothesis' example database out of the repository root.
    return subprocess.call(command, cwd=HERE, env=env)


if __name__ == "__main__":
    sys.exit(main())
