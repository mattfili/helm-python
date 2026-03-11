# Getting Started Example

## What This Demonstrates
Foundation pattern for all fairlead usage: create instance, register skills, call typed operations, discover via search.

## Key Patterns

```python
# Create with default permissions
agent = Fairlead(FairleadOptions(default_permission="allow"))

# Register skills with chaining
agent.use(fs()).use(git())

# Call via attribute access — returns typed objects
status = await agent.git.status()       # -> GitStatus
result = await agent.fs.read_file(path="README.md")  # -> dict[str, str]

# Discover operations
results = agent.search("file")  # -> list[SearchResult]
```

## Key Imports
```python
from fairlead import Fairlead, FairleadOptions, fs, git, grep, edit, http, shell
```

## How to Replicate This Pattern
1. Import `Fairlead`, `FairleadOptions`, and desired skill factories
2. Create `Fairlead(FairleadOptions(default_permission="allow"))` for scripts (no interactive prompts)
3. Chain `.use()` calls to register skills
4. Use `await agent.<skill>.<operation>(...)` for typed calls
5. Use `agent.search(query)` to find operations

## Common Mistakes
- Forgetting `await` — all operations are async
- Using `agent.call("fs.read_file", {"path": "x"})` when attribute access is simpler for direct use
- Not setting `default_permission="allow"` in non-interactive scripts (operations will raise `PermissionDeniedError`)

## Related Examples
- [02-permissions](../02-permissions/) — controlling access to operations
- [03-code-mode](../03-code-mode/) — using `.call()` for programmatic chaining
