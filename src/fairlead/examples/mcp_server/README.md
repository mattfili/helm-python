# 04 — MCP Server

Expose fairlead as an MCP (Model Context Protocol) server. Claude Desktop and other MCP clients get a 2-tool interface: `search` to discover operations and `call` to invoke them.

## What You'll Learn

- Configuring fairlead skills for MCP exposure
- Starting the MCP server with `serve()`
- Claude Desktop integration via `claude_desktop_config.json`
- The 2-tool MCP interface (`search` + `call`)

## Run It

```bash
pip install -e ../..
python server.py
```

The server reads JSON-RPC messages from stdin and writes responses to stdout. To integrate with Claude Desktop, add the config from `claude_desktop_config.json` to your Claude Desktop settings.

## How It Works

The MCP server exposes exactly two tools to any connected client:

1. **`search`** — Find operations by keyword (e.g., `{"query": "git"}`)
2. **`call`** — Invoke an operation by qualified name (e.g., `{"name": "git.status"}`)

This keeps the tool count constant regardless of how many skills you register. An LLM searches first, then calls what it finds.

## Claude Desktop Integration

Copy the contents of `claude_desktop_config.json` into your Claude Desktop config file:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
