# helm

A typed Python framework for AI agents. Agents call typed functions instead of parsing CLI stdout.

## The Problem

Traditional agent tool use is string-in, string-out:

```python
output = bash("git status --porcelain")
files = parse_git_status(output)  # fragile string parsing
```

Every tool call is a round-trip. The agent sends text, waits for text back, parses it, then decides what to do next. Five operations = five round-trips, each burning context window tokens on serialization overhead.

Helm fixes both problems: **typed operations** eliminate parsing, and **Code Mode** eliminates round-trips.

```python
status = await agent.git.status()
print(status.branch)          # str — not a string to parse
print(status.staged)          # list[FileChange] — real objects
print(status.untracked)       # list[str]
```

## Install

```bash
uv pip install -e .

# with dev dependencies
uv pip install -e ".[dev]"
```

Requires Python 3.12+. Zero runtime dependencies.

## Quick Start

```python
import asyncio
from helm import create_helm, HelmOptions
from helm.skills import fs, git

async def main():
    agent = (
        create_helm(HelmOptions(default_permission="allow"))
        .use(fs())
        .use(git())
    )

    # Typed file operations
    result = await agent.fs.read_file("pyproject.toml")
    print(result["content"])

    # Typed git operations
    status = await agent.git.status()
    print(f"Branch: {status.branch}")
    print(f"Staged: {len(status.staged)} files")

asyncio.run(main())
```

## Code Mode

Code Mode is what makes helm different from a bag of tools.

Standard MCP gives an agent one tool per operation. An API with 500 endpoints means 500 tool definitions stuffed into the context window before the agent writes a single token. Worse, every operation is a round-trip — the agent calls one tool, waits for the result, reasons about it, then calls the next.

Code Mode compresses everything into **2 tools** (`search` + `call`) and lets the agent **chain operations programmatically** in a single invocation:

```
Standard MCP (5 round-trips):              Code Mode (1 round-trip):

agent → tool: git.status                   agent → call tool:
agent ← result                               status = helm.call("git.status")
agent → tool: fs.read_file                    if status.branch != "main":
agent ← result                                  diff = helm.call("git.diff")
agent → tool: git.diff                          files = [d.path for d in diff]
agent ← result                                  for f in files:
agent → tool: grep.search                          matches = helm.call("grep.search",
agent ← result                                       {"pattern": "TODO"})
agent → tool: edit.replace                       helm.call("edit.replace", {...})
agent ← result                             agent ← final result
```

The agent writes a script that reads, branches, and loops over typed results — the same way a human developer would. No round-trips, no string parsing, no context window bloat. And because helm operations return typed objects (not strings), the agent can dot-access fields, iterate over lists, and branch on real values instead of regex-matching text.

### Programmatic Tool Chaining

This is the core capability. An agent can compose multiple operations in a single execution context — reading results, making decisions, and acting on them without returning to the LLM between each step:

```python
# The agent generates this as a single tool call.
# All 4 operations execute in one round-trip.

status = await agent.call("git.status")

for f in status.untracked:
    content = await agent.call("fs.read_file", {"path": f})
    matches = await agent.call("grep.search", {"pattern": "FIXME"})
    if any(f in m for m in matches):
        await agent.call("git.add", {"paths": [f]})
```

This works because `call()` returns typed Python objects, not serialized strings. The agent can use `if`, `for`, and variable assignment to build real control flow around tool results — something that's impossible when every tool call is a separate LLM round-trip.

### Why This Matters for Sandboxed Agents

Sandboxed agents (containers, VMs, restricted shells) can't install arbitrary tools or call APIs directly. Helm gives them a typed, permissioned surface that works within the sandbox. Code Mode means the agent can do complex multi-step work without the latency penalty of one-tool-at-a-time execution — critical for agents that need to stay responsive while operating under constraints.

### Running the MCP Server

```bash
# Start the server (registers all built-in skills)
python -m helm

# Or use the CLI entry point
helm-mcp
```

The server speaks JSON-RPC 2.0 over stdio. An agent sees exactly 2 tools:

- **`search`** — find operations by name, description, or tags
- **`call`** — invoke any operation by qualified name with keyword arguments

### OpenAPI Skill Factory

Any OpenAPI 3.x spec becomes a helm skill. Load a 2,500-endpoint API, expose it via Code Mode, and the agent sees 2 tools instead of 2,500:

```python
from helm import create_helm, HelmOptions, openapi, serve
import asyncio

petstore = openapi(
    "https://petstore3.swagger.io/api/v3/openapi.json",
    name="petstore",
    base_url="https://petstore3.swagger.io/api/v3",
    default_permission="allow",
)

agent = create_helm(HelmOptions(default_permission="allow")).use(petstore)

async def main():
    # Every endpoint is a typed operation
    pets = await agent.call("petstore.list_pets", {"query": {"limit": "10"}})
    pet = await agent.call("petstore.get_pet", {"petId": 1})

    # Chain with built-in skills
    await agent.call("fs.write_file", {
        "path": "pet.json",
        "content": str(pet)
    })

asyncio.run(main())
```

Spec sources: dict, JSON string, file path, or URL. YAML specs work too (requires `pyyaml`).

## Built-in Skills

### fs — File System

| Operation | Description |
|-----------|-------------|
| `read_file(path)` | Read file contents |
| `write_file(path, content)` | Write/create a file |
| `readdir(path, opts)` | List directory entries with optional glob |
| `mkdir(path)` | Create directories recursively |
| `stat(path)` | Get file metadata |
| `rm(path)` | Delete files/directories |
| `rename(old, new)` | Move/rename files |
| `cwd()` | Get current working directory |

### git — Version Control

| Operation | Description |
|-----------|-------------|
| `status()` | Branch, staged, unstaged, untracked files |
| `diff(opts)` | File changes with line counts |
| `log(opts)` | Commit history |
| `show(ref, opts)` | Commit or file content at a ref |
| `add(paths)` | Stage files |
| `commit(message)` | Create a commit |
| `branch_list()` | List branches |
| `branch_create(name, opts)` | Create a branch |
| `checkout(ref)` | Switch branches |

### grep — File Search

| Operation | Description |
|-----------|-------------|
| `search(pattern, opts)` | Regex search across files with context lines, glob filtering, .gitignore support |

### edit — Text Editing

| Operation | Description |
|-----------|-------------|
| `replace(path, old, new, opts)` | Replace string occurrences |
| `insert(path, line, content)` | Insert text at a line number |
| `remove_lines(path, start, end)` | Delete a range of lines |
| `apply(path, edits)` | Batch atomic edits |

### shell — Command Execution

| Operation | Description |
|-----------|-------------|
| `dangerous_exec(command, opts)` | Run a shell command with timeout, env, and cwd support |

### http — HTTP Client

| Operation | Description |
|-----------|-------------|
| `fetch(url, opts)` | Make HTTP requests |
| `json(url, opts)` | Fetch and parse JSON |

## Permissions

Every operation has a permission level: `"allow"`, `"ask"`, or `"deny"`.

```python
agent = create_helm(HelmOptions(
    permissions={
        "fs.read_file": "allow",    # always permitted
        "fs.write_file": "ask",     # requires approval
        "fs.rm": "deny",            # always blocked
        "git.*": "allow",           # wildcard match
    },
    default_permission="ask",
    on_permission_request=my_approval_handler,
))
```

Resolution order: exact match → wildcard → operation default → global default.

Permissions are enforced on every `call()` — including inside chained scripts. An agent can't escalate by composing operations; each individual call still checks permissions.

## Search & Discovery

Agents can discover operations dynamically:

```python
results = agent.search("file read")
for r in results[:5]:
    print(f"{r.qualified_name}: {r.description}")
```

## Custom Skills

```python
from helm import define_skill, OperationDef

weather = define_skill(
    name="weather",
    description="Weather operations",
    operations={
        "forecast": OperationDef(
            description="Get forecast for a city",
            default_permission="allow",
            handler=lambda city: {"temp": 72, "sky": "sunny"},
        )
    },
)

agent = create_helm().use(weather)
forecast = await agent.weather.forecast("Seattle")
```

## Development

```bash
# run tests
uv run pytest

# type check
uv run mypy src/helm

# lint
uv run ruff check src/ tests/
```

## License

MIT
