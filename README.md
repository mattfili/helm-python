# fairlead

Give an AI agent typed access to any API — no matter how large.

## The Idea

What happens when you hand an agent the entire sklearn API? Or pytorch? Or every endpoint of the GitHub API?

With standard MCP, you can't. 500 endpoints = 500 tool definitions crammed into the context window before the agent writes a single token. The model chokes, the latency spikes, and you've burned your budget on tool descriptions.

Fairlead compresses **any API surface** into **2 tools**: `search` and `call`. The agent discovers what it needs, calls it with typed arguments, and chains results together — programmatically, in a single round-trip.

```python
from fairlead import create_fairlead, FairleadOptions, openapi

# Turn any OpenAPI spec into a skill — 50 endpoints or 5,000
github = openapi(
    "path/to/github_openapi.json",
    name="github",
    base_url="https://api.github.com",
    headers={"Authorization": "Bearer ..."},
    default_permission="allow",
)

agent = create_fairlead(FairleadOptions(default_permission="allow")).use(github)

# The agent sees 2 tools. It searches, discovers, and chains:
results = agent.search("repository issues")
issues = await agent.call("github.list_repo_issues", {
    "owner": "anthropics", "repo": "claude-code"
})
```

Now imagine the same pattern with sklearn:

```python
sklearn_skill = define_skill(
    name="sklearn",
    description="Scikit-learn machine learning library",
    operations={
        "train_test_split": OperationDef(
            description="Split arrays into train and test subsets",
            handler=sklearn.model_selection.train_test_split,
        ),
        "fit_random_forest": OperationDef(
            description="Fit a random forest classifier",
            handler=lambda X, y, **kw: RandomForestClassifier(**kw).fit(X, y),
        ),
        "cross_val_score": OperationDef(
            description="Evaluate with cross-validation",
            handler=sklearn.model_selection.cross_val_score,
        ),
        # ... every estimator, transformer, metric
    },
)
```

Register sklearn + pandas + pytorch as skills, serve it as an MCP server, and point Claude at a Kaggle competition. The agent can search for the right estimator, load data, engineer features, train models, and evaluate — all through typed operations, all with permission controls, all composable in a single code block.

**That's the point.** Fairlead turns any API into something an AI agent can actually use at scale.

## Install

```bash
pip install -e .

# with dev dependencies
pip install -e ".[dev]"
```

Requires Python 3.12+. Zero runtime dependencies.

## How It Works

### 2 Tools Instead of 2,000

An MCP server built with fairlead exposes exactly 2 tools:

| Tool | Purpose |
|------|---------|
| `search` | Find operations by name, description, or tags |
| `call` | Invoke any operation by qualified name with keyword arguments |

The agent doesn't need to know the full API upfront. It searches, discovers what's relevant, and calls it. This works whether your API surface has 6 operations or 6,000.

### Typed Results, Not Strings

Operations return Python objects, not serialized text:

```python
status = await agent.git.status()
status.branch          # str
status.staged          # list[FileChange]
status.untracked       # list[str]
```

The agent can dot-access fields, iterate lists, and branch on real values. No regex. No parsing.

### Programmatic Chaining (Code Mode)

Instead of one tool call per round-trip, the agent writes a script that chains operations together:

```python
# One round-trip. Four operations. Real control flow.
status = await agent.call("git.status")

for f in status.untracked:
    content = await agent.call("fs.read_file", {"path": f})
    matches = await agent.call("grep.search", {"pattern": "FIXME", "path": f})
    if matches:
        await agent.call("git.add", {"paths": [f]})
```

Standard MCP would need 4+ round-trips, each burning context window tokens and adding latency.

### Permissions on Every Call

Every operation checks permissions — even inside chained scripts. An agent can't escalate by composing operations:

```python
agent = create_fairlead(FairleadOptions(
    permissions={
        "fs.read_file": "allow",     # always permitted
        "fs.write_file": "ask",      # requires approval
        "fs.rm": "deny",             # always blocked
        "sklearn.*": "allow",        # wildcard: all sklearn ops
    },
    default_permission="ask",
    on_permission_request=my_handler,
))
```

Resolution order: exact match > wildcard > operation default > global default.

## Quick Start

```python
import asyncio
from fairlead import create_fairlead, FairleadOptions
from fairlead.skills import fs, git, grep

async def main():
    agent = (
        create_fairlead(FairleadOptions(default_permission="allow"))
        .use(fs())
        .use(git())
        .use(grep())
    )

    status = await agent.git.status()
    print(f"On branch {status.branch}, {len(status.staged)} staged files")

    results = await agent.grep.search(pattern="TODO", path="src/")
    for match in results:
        print(f"  {match.path}:{match.line_number}: {match.text}")

asyncio.run(main())
```

## OpenAPI Skill Factory

Any OpenAPI 3.x spec becomes a fairlead skill instantly. Load a spec from a dict, JSON string, file path, or URL:

```python
from fairlead import create_fairlead, FairleadOptions, openapi, serve
import asyncio

petstore = openapi(
    "https://petstore3.swagger.io/api/v3/openapi.json",
    name="petstore",
    base_url="https://petstore3.swagger.io/api/v3",
    default_permission="allow",
)

agent = create_fairlead(FairleadOptions(default_permission="allow")).use(petstore)

async def main():
    pets = await agent.call("petstore.list_pets", {"query": {"limit": "10"}})
    pet = await agent.call("petstore.get_pet", {"petId": 1})

    await agent.call("fs.write_file", {
        "path": "pet.json",
        "content": str(pet)
    })

asyncio.run(main())
```

YAML specs work too (requires `pyyaml`).

## Custom Skills

Wrap any Python library as a fairlead skill:

```python
from fairlead import define_skill, OperationDef

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

agent = create_fairlead().use(weather)
forecast = await agent.weather.forecast("Seattle")
```

This is how you'd wrap sklearn, pytorch, pandas, or any library with a large API surface. Each function becomes a discoverable, permissioned operation.

## MCP Server

Serve any fairlead agent as an MCP server for Claude Desktop or any MCP client:

```bash
# Start with built-in skills (fs, git, grep, edit, http, shell)
python -m fairlead

# Or use the CLI entry point
fairlead-mcp
```

The server speaks JSON-RPC 2.0 over stdio. The agent sees 2 tools: `search` and `call`.

## Built-in Skills

| Skill | Operations |
|-------|-----------|
| **fs** | `read_file`, `write_file`, `readdir`, `mkdir`, `stat`, `rm`, `rename`, `cwd` |
| **git** | `status`, `diff`, `log`, `show`, `add`, `commit`, `branch_list`, `branch_create`, `checkout` |
| **grep** | `search` — regex across files with context, glob filtering, .gitignore support |
| **edit** | `replace`, `insert`, `remove_lines`, `apply` (batch atomic edits) |
| **http** | `fetch`, `json` |
| **shell** | `dangerous_exec` — run commands with timeout, env, cwd |

## Examples

```bash
# List all examples
python -m fairlead.examples

# Run one
python -m fairlead.examples.getting_started
python -m fairlead.examples.openapi_skill
python -m fairlead.examples.github_code_mode
```

## Development

```bash
uv run pytest                      # tests
uv run mypy src/fairlead           # type check
uv run ruff check src/ tests/      # lint
```

## License

MIT
