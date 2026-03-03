# helm

A typed Python framework for AI agents. Agents call typed functions instead of parsing CLI stdout.

## The Problem

Traditional agent tool use looks like this:

```python
output = bash("git status --porcelain")
files = parse_git_status(output)  # fragile string parsing
```

Helm replaces that with structured, typed operations:

```python
status = await agent.git.status()
print(status.branch)          # str
print(status.staged)          # list[FileChange]
print(status.untracked)       # list[str]
```

No string parsing. Type-safe inputs and outputs. Fine-grained permission control.

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

## Search & Discovery

Agents can discover operations dynamically:

```python
results = agent.search("file read")
for r in results[:5]:
    print(f"{r.qualified_name}: {r.description}")
```

## Code Mode (MCP Server)

For APIs with hundreds or thousands of operations, loading every operation into an agent's context window is impractical. Code Mode compresses any number of operations into just 2 MCP tools: `search` and `call`.

```bash
# Start the MCP server (registers all built-in skills)
python -m helm

# Or use the CLI entry point
helm-mcp
```

The server speaks JSON-RPC 2.0 over stdio. An agent sees exactly 2 tools:

- **`search`** — find operations by name, description, or tags
- **`call`** — invoke any operation by qualified name with keyword arguments

### Programmatic call()

You can also call operations by name directly:

```python
result = await agent.call("git.status")
result = await agent.call("fs.read_file", {"path": "pyproject.toml"})
```

### OpenAPI Skill Factory

Generate a Skill from any OpenAPI 3.x spec:

```python
from helm import create_helm, HelmOptions, openapi, serve

# Load from dict, JSON string, file path, or URL
petstore = openapi(
    "https://petstore3.swagger.io/api/v3/openapi.json",
    name="petstore",
    base_url="https://petstore3.swagger.io/api/v3",
    default_permission="allow",
)

agent = create_helm(HelmOptions(default_permission="allow")).use(petstore)

# Every endpoint becomes a typed operation
pets = await agent.call("petstore.list_pets", {"query": {"limit": "10"}})
pet = await agent.call("petstore.get_pet", {"petId": 1})
```

Load a 2,500-endpoint API, expose it via MCP, and the agent sees 2 tools instead of 2,500.

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
