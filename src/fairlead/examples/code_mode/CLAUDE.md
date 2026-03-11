# Code Mode Example

## What This Demonstrates
Server-side Code Mode: chaining `agent.call()` with Python control flow — the key differentiator of fairlead.

## Key Patterns

```python
# Simple chain — read file, then search its content
content = await agent.call("fs.read_file", {"path": "README.md"})
matches = await agent.call("grep.search", {"pattern": "fairlead", "path": "."})

# Conditional logic on typed results
status = await agent.call("git.status")
if status.untracked:
    await agent.call("git.add", {"paths": status.untracked})

# Loop + batch
listing = await agent.call("fs.readdir", {"path": "src"})
for entry in listing["entries"]:
    if entry.is_file:
        stat = await agent.call("fs.stat", {"path": entry.path})
        print(f"{entry.name}: {stat.size} bytes")
```

## Key Imports
```python
from fairlead import Fairlead, FairleadOptions, fs, git, grep
```

## How to Replicate This Pattern
1. Use `agent.call("skill.operation", {"key": "value"})` for dynamic dispatch
2. Store results in variables — they're typed Python objects
3. Use standard Python control flow (if/for/try) on results
4. Build multi-step workflows as regular async functions

## Common Mistakes
- Using attribute access (`agent.fs.read_file()`) when you need dynamic dispatch — use `.call()` for programmatic operation names
- Forgetting that `.call()` takes a dict of **keyword arguments**, not positional args
- Not handling `PermissionDeniedError` in chains — one denied operation breaks the whole chain

## Related Examples
- [01-getting-started](../01-getting-started/) — attribute access (simpler alternative)
- [04-mcp-server](../04-mcp-server/) — `.call()` is the same interface MCP clients use
