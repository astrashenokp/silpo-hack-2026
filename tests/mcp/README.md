# MCP QA tools

Owner: Polina.

| Tool | Package | Used for |
|---|---|---|
| MCP Inspector | `@modelcontextprotocol/inspector` 2.6.0 | Connect to the Silpo MCP server, complete OAuth in the browser, list tools and schemas, call read tools by hand |
| Python MCP SDK | `mcp` 2.2.0 (`requirements.txt`) | `probe_mcp.py`: scripted `tools/list` with a bearer token, using the same SDK as the backend |
| Playwright MCP | `@playwright/mcp` 0.0.80 | Browser automation for Claude Code |
| Chrome DevTools MCP | `chrome-devtools-mcp` 1.9.0 | Console, network and performance traces for Claude Code |

`servers.json` describes these servers for the Inspector (`--config servers.json --server <name>`).

## Setup (once)

```powershell
cd tests/mcp
npm.cmd ci
```

The Python part shares `tests/.venv` with the contract fuzzing (see `tests/contract/README.md`).

## Check the local servers

```powershell
npm.cmd run tools:playwright       # lists 24 tools
npm.cmd run tools:chrome-devtools  # lists 29 tools
```

## Silpo MCP (authorized demo account only)

1. Interactive: `npm.cmd run inspector` opens the Inspector web UI. Connect to
   `https://mcp.silpo.ua/mcp` over HTTP and finish OAuth in the browser, then list the tools.
   The web UI was not started during setup.
2. Scripted, with the access token only in the environment:

   ```powershell
   $env:MCP_ACCESS_TOKEN = '<token>'
   & tests/.venv/Scripts/python.exe tests/mcp/probe_mcp.py --out tests/mcp/reports/silpo-tools.json
   Remove-Item Env:MCP_ACCESS_TOKEN
   ```

   `probe_mcp.py --url <url>` works with any Streamable HTTP server; it was checked against a
   local Playwright MCP. The Inspector CLI equivalent is
   `npx.cmd mcp-inspector --cli --config servers.json --server silpo --method tools/list --header "Authorization: Bearer <token>"`.

Record tool names, required cart/store context and redacted errors in
`docs/qa/test-results.md`. Never commit tokens, account data or raw provider payloads;
`reports/` is ignored by git.

## Claude Code registration

Playwright MCP and Chrome DevTools MCP are registered in Polina's Claude Code with local
scope (this project on her machine only, not in the repository):

```powershell
claude mcp add-json -s local playwright '{"type":"stdio","command":"cmd","args":["/c","npx","-y","@playwright/mcp@0.0.80","--headless","--isolated"]}'
claude mcp add-json -s local chrome-devtools '{"type":"stdio","command":"cmd","args":["/c","npx","-y","chrome-devtools-mcp@1.9.0","--headless","--isolated"]}'
```

`claude mcp list` checks their health. Their tools appear after the Claude Code session
restarts. Remove `--headless` to watch the browser.

`github/github-mcp-server` is not registered: it needs a personal access token, and the
`gh` CLI already covers issues and pull requests.
