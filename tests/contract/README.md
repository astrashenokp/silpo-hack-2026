# Contract fuzzing: Schemathesis

Owner: Polina. Generates requests from `packages/contracts/openapi.json` and checks the
running API against it: server errors, undocumented status codes, response schemas,
unsupported methods and requests the API rejects although the schema allows them.

## Setup (once, repository root, PowerShell)

The QA tools share one virtual environment, separate from the backend's:

```powershell
python -m venv tests/.venv
& tests/.venv/Scripts/python.exe -m pip install -r tests/contract/requirements.txt -r tests/mcp/requirements.txt
```

## Run (API on `127.0.0.1:8000`)

```powershell
& tests/.venv/Scripts/python.exe tests/contract/run_schemathesis.py --max-examples 25
```

The runner opens one demo session and sends its cookie with every request. It excludes
`/api/auth/*` and `/api/integrations/silpo/*`, so fuzzing never contacts Silpo or FatSecret.
Extra arguments go to `schemathesis run` (for example `--max-examples 100` or
`--checks not_a_server_error`). `CONTRACT_BASE_URL` selects another API. JUnit reports are
written to `tests/contract/reports/`; every failure prints a `curl` command to reproduce it.

Fuzz demo deployments only: a run creates hundreds of plans and previews.
