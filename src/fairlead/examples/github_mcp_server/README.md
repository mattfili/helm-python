# 11 — GitHub MCP Server

Expose the GitHub API to Claude Desktop as an MCP server. 18 read-only GitHub endpoints become searchable and callable tools — with permission controls.

## What You'll Learn

- Serving an `openapi()` skill as an MCP server
- Using wildcard permissions (`"github.*": "allow"`) with a deny default
- Configuring Claude Desktop to use the server

## Run It

```bash
pip install -e ../..
python server.py
```

The server reads JSON-RPC from stdin and writes to stdout. To use with Claude Desktop, add the config below.

## Claude Desktop Setup

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
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

Set `GITHUB_TOKEN` in your environment for 5,000 req/hr:

```bash
export GITHUB_TOKEN=ghp_your_token_here
```

## How It Works

The server exposes exactly 2 MCP tools:
- **search(query)** — discover GitHub operations (e.g., search "repo" to find repo-related endpoints)
- **call(name, args)** — invoke a GitHub endpoint (e.g., `call("github.get_repo", {"owner": "python", "repo": "cpython"})`)

All 18 GitHub operations are allowed via the `"github.*": "allow"` wildcard. The global default is `"deny"`, so only GitHub operations are accessible.
