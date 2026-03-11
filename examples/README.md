# helm-python Examples

Hands-on examples showing how to use helm's typed operations, permissions, Code Mode, MCP server, and extensibility features.

## Prerequisites

- Python 3.12+
- helm installed: `pip install -e ..` (from this directory) or `pip install helm`

## Examples

| # | Example | What You'll Learn |
|---|---------|-------------------|
| 01 | [Getting Started](01-getting-started/) | Create a Helm instance, register skills, call typed operations, search |
| 02 | [Permissions](02-permissions/) | Permission rules, wildcards, `on_permission_request` callback |
| 03 | [Code Mode](03-code-mode/) | Chain `.call()` invocations with branching, looping, variables |
| 04 | [MCP Server](04-mcp-server/) | Expose helm as an MCP server for Claude Desktop |
| 05 | [Chat Client](05-chat-client/) | Terminal chat app using helm's MCP server + Anthropic API |
| 06 | [Custom Skills](06-custom-skills/) | Define domain-specific skills with `define_skill()` |
| 07 | [OpenAPI Skill](07-openapi-skill/) | Turn any OpenAPI spec into a helm skill |
| 08 | [GitHub OpenAPI](08-github-openapi/) | Real API (GitHub) via `openapi()` — discovery, auth headers, typed calls |
| 09 | [GitHub Code Mode](09-github-code-mode/) | Multi-step workflows: search + rank, org scan, repo comparison |
| 10 | [GitHub Explorer](10-github-explorer/) | Combine OpenAPI + custom skill + Code Mode in one workflow |
| 11 | [GitHub MCP Server](11-github-mcp-server/) | Serve GitHub API to Claude Desktop with permission controls |

## Progression

```
01 (foundation) -> 02 (permissions) -> 03 (code mode) -> 04 (MCP server) -> 05 (chat client)
       |
       v
      06 (custom skills) -> 07 (openapi) -> 08 (github openapi) -> 09 (github code mode)
                                                     |                       |
                                                     v                       v
                                              11 (github MCP)       10 (github explorer)
```

Examples 08–11 use the real GitHub API. Set `GITHUB_TOKEN` for higher rate limits.

Start with **01-getting-started** — every other example builds on it.

## Running an Example

```bash
cd 01-getting-started
pip install -e ../..   # install helm from source
python main.py
```

Each example is self-contained. Copy any example directory into a new project to use as a starting point.
