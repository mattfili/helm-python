# GitHub MCP Server Example

## What This Demonstrates
Serving a real API (GitHub) as an MCP server with wildcard permissions and a deny-by-default policy.

## Key Patterns

```python
from helm import Helm, HelmOptions, openapi, serve

# Load GitHub API with auth headers
github = openapi(spec_path, name="github", headers=headers, default_permission="allow")

# Allow all GitHub ops, deny everything else
agent = Helm(HelmOptions(
    permissions={"github.*": "allow"},
    default_permission="deny",
))
agent.use(github)

await serve(agent)  # reads stdin, writes stdout (JSON-RPC)
```

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "github": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/examples/11-github-mcp-server"
    }
  }
}
```

## Key Imports
```python
from helm import Helm, HelmOptions, openapi, serve
```

## How to Replicate This Pattern
1. Load an API spec with `openapi()`, passing auth headers
2. Create a `Helm` instance with wildcard permissions and `default_permission="deny"`
3. Register the skill and call `await serve(agent)`
4. Configure Claude Desktop to point at the server script

## Common Mistakes
- Using `default_permission="deny"` without setting `"github.*": "allow"` — all calls fail
- Forgetting `User-Agent` header — GitHub returns 403
- Not setting `GITHUB_TOKEN` in the shell environment where Claude Desktop runs
- Running `serve()` without `asyncio.run()` — it's an async function

## Related Examples
- [04-mcp-server](../04-mcp-server/) — MCP server basics with built-in skills
- [08-github-openapi](../08-github-openapi/) — GitHub API setup and discovery
- [02-permissions](../02-permissions/) — permission rules and wildcards
