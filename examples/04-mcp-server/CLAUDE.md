# MCP Server Example

## What This Demonstrates
Exposing helm as an MCP server with selected skills and permissions, ready for Claude Desktop integration.

## Key Patterns

```python
# Configure and serve
agent = Helm(HelmOptions(default_permission="allow"))
agent.use(fs()).use(git()).use(grep())
await serve(agent)  # reads stdin, writes stdout (JSON-RPC)
```

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "helm": {
      "command": "python",
      "args": ["path/to/server.py"]
    }
  }
}
```

## Key Imports
```python
from helm import Helm, HelmOptions, serve, fs, git, grep, edit, http, shell
```

## How to Replicate This Pattern
1. Create a `Helm` instance with desired permissions
2. Register only the skills you want to expose
3. Call `await serve(agent)` — it handles the JSON-RPC protocol
4. Point Claude Desktop at your server script

## Common Mistakes
- Registering skills you don't want exposed — the MCP server exposes ALL registered skills
- Using `default_permission="deny"` without an `on_permission_request` callback — MCP calls will fail silently
- Running `serve()` without `asyncio.run()` — it's an async function

## Related Examples
- [01-getting-started](../01-getting-started/) — basic skill registration
- [05-chat-client](../05-chat-client/) — building a client that talks to this server
