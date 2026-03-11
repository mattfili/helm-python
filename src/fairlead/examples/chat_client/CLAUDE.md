# Chat Client Example

## What This Demonstrates
A complete MCP client: subprocess management, JSON-RPC transport, and Anthropic API integration in a terminal chat app.

## Key Patterns

```python
# Spawn MCP server as subprocess
process = await asyncio.create_subprocess_exec(
    "python", "server.py",
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
)

# Send JSON-RPC message
request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
process.stdin.write(json.dumps(request).encode() + b"\n")
response = json.loads(await process.stdout.readline())

# Anthropic tool_use loop
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    tools=mcp_tools,
    messages=messages,
)
# Route tool calls through MCP client
```

## Key Imports
```python
import anthropic   # pip install anthropic
import asyncio, json, subprocess
```

## How to Replicate This Pattern
1. Write a server script (see 04-mcp-server)
2. Spawn it as a subprocess with stdin/stdout pipes
3. Send `initialize` and `tools/list` to discover tools
4. Feed tool definitions to the Anthropic API
5. Route `tool_use` responses through the MCP client
6. Feed tool results back to the API as `tool_result`

## Common Mistakes
- Forgetting to flush stdout after writing JSON-RPC messages
- Not handling `notifications/initialized` (send after `initialize`)
- Blocking on subprocess.communicate() instead of using line-by-line IO
- Not setting `ANTHROPIC_API_KEY` environment variable

## Related Examples
- [04-mcp-server](../04-mcp-server/) — the server this client connects to
- [03-code-mode](../03-code-mode/) — server-side alternative to LLM-driven tool use
