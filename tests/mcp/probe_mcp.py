"""List the tools an MCP server exposes over Streamable HTTP (owner: Polina).

Usage (repository root, QA virtual environment):
    & tests/.venv/Scripts/python.exe tests/mcp/probe_mcp.py [--url URL] [--out FILE]

The bearer token is read from MCP_ACCESS_TOKEN so it stays out of shell history and
reports. The default URL is SILPO_MCP_URL or https://mcp.silpo.ua/mcp; without a token
the Silpo server is expected to refuse the session, which only proves it is reachable.
"""

import argparse
import asyncio
import json
import os
import sys

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


def summarize(tool):
    schema = tool.input_schema or {}
    description = (tool.description or "").strip()
    return {
        "name": tool.name,
        "summary": description.splitlines()[0] if description else "",
        "required": schema.get("required", []),
        "properties": sorted(schema.get("properties", {})),
    }


async def probe(url, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx2.AsyncClient(headers=headers, follow_redirects=True, timeout=30) as http_client:
        async with streamable_http_client(url, http_client=http_client) as (read, write):
            async with ClientSession(read, write) as session:
                info = await session.initialize()
                tools = (await session.list_tools()).tools
    return {
        "url": url,
        "server": info.server_info.name,
        "version": info.server_info.version,
        "protocol": info.protocol_version,
        "tools": [summarize(tool) for tool in tools],
    }


def root_cause(error):
    # anyio wraps transport failures in exception groups; show the first real error.
    while isinstance(error, BaseExceptionGroup) and error.exceptions:
        error = error.exceptions[0]
    return error


def main():
    parser = argparse.ArgumentParser(description="List the tools of an MCP server.")
    parser.add_argument("--url", default=os.getenv("SILPO_MCP_URL", "https://mcp.silpo.ua/mcp"))
    parser.add_argument("--out", help="also write the JSON summary to this file")
    args = parser.parse_args()
    try:
        report = asyncio.run(probe(args.url, os.getenv("MCP_ACCESS_TOKEN")))
    except BaseException as error:
        cause = root_cause(error)
        print(f"Probe of {args.url} failed: {type(cause).__name__}: {cause}", file=sys.stderr)
        return 1
    print(f"{report['server']} {report['version']} (protocol {report['protocol']}): "
          f"{len(report['tools'])} tools")
    for tool in report["tools"]:
        required = ", ".join(tool["required"]) or "-"
        print(f"  {tool['name']}  required: {required}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as file:
            json.dump(report, file, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
