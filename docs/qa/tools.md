# QA toolkit

Where each kind of check lives (owner: Polina). Record every run in
[test results](test-results.md) and defects in [the bug list](bugs.md).

| Layer | Tool and version | Location | Command |
|---|---|---|---|
| HTTP golden flow and failure scenarios | pytest + httpx | `tests/e2e/` | `python -m pytest tests/e2e` |
| API contract fuzzing | Schemathesis 4.26.1 | `tests/contract/` | `tests/.venv/Scripts/python.exe tests/contract/run_schemathesis.py` |
| Browser flows, desktop and mobile | Playwright 1.63.0 | `tests/ui/specs/` | `npm.cmd test` in `tests/ui` |
| Accessibility, WCAG 2.1 AA | axe-core via `@axe-core/playwright` 4.13.0 | `tests/ui/specs/a11y.spec.ts` | `npm.cmd test` in `tests/ui` |
| Performance and best practices | Lighthouse 13.4.1 | `tests/ui/lighthouse.mjs` | `npm.cmd run lighthouse` in `tests/ui` |
| Silpo MCP tools and OAuth | MCP Inspector 2.6.0, Python MCP SDK 2.2.0 | `tests/mcp/` | `npm.cmd run inspector`, `probe_mcp.py` |
| Exploratory browser QA with Claude | Playwright MCP 0.0.80, Chrome DevTools MCP 1.9.0 | Claude Code local configuration | Ask Claude in a session |

## Scenario coverage ([QA and Demo](../QA_DEMO.md))

| Scenario | Tools |
|---|---|
| Next.js / Python contract, invalid inputs | e2e suite, Schemathesis |
| Desktop, narrow screen and keyboard | Playwright `desktop` and `mobile` projects, keyboard spec, axe |
| UI wired to the API, demo/live labels | Playwright `api-wiring` spec, Playwright MCP |
| Hosted run | Every suite with `E2E_BASE_URL`, `UI_BASE_URL` or `CONTRACT_BASE_URL` set to the deployed origin; Lighthouse on the public URL |
| Real MCP interaction | MCP Inspector and `probe_mcp.py` with the authorized demo account |
| FatSecret app visibility | Manual check in the FatSecret app, recorded in test results |

## Setup on a new machine (PowerShell, repository root)

```powershell
python -m venv tests/.venv
& tests/.venv/Scripts/python.exe -m pip install -r tests/contract/requirements.txt -r tests/mcp/requirements.txt
cd tests/ui; npm.cmd ci; npx.cmd playwright install chromium; cd ../..
cd tests/mcp; npm.cmd ci; cd ../..
```

Then register the two browser MCP servers in Claude Code as shown in `tests/mcp/README.md`.
