# Permissions Example

## What This Demonstrates
The full permission resolution chain: exact match, wildcard, operation default, global default, and interactive approval via callback.

## Key Patterns

```python
# Permission policy with exact and wildcard rules
agent = Fairlead(FairleadOptions(
    permissions={
        "fs.read_file": "allow",     # exact match
        "fs.write_file": "deny",     # exact match
        "git.*": "allow",            # wildcard — all git ops
    },
    default_permission="ask",        # global fallback
))

# Catch denied operations
try:
    await agent.fs.write_file(path="x", content="y")
except PermissionDeniedError as e:
    print(f"Blocked: {e.qualified_name}")

# Interactive approval callback
def approve(operation: str, args: list) -> bool:
    return input(f"Allow {operation}? [y/n] ") == "y"

agent = Fairlead(FairleadOptions(
    default_permission="ask",
    on_permission_request=approve,
))
```

## Key Imports
```python
from fairlead import Fairlead, FairleadOptions, PermissionDeniedError, fs, git
```

## How to Replicate This Pattern
1. Define a `permissions` dict mapping qualified names or wildcards to `"allow"`, `"ask"`, or `"deny"`
2. Set `default_permission` for the global fallback
3. Optionally provide `on_permission_request` callback for `"ask"` operations
4. Wrap risky calls in try/except for `PermissionDeniedError`

## Common Mistakes
- Setting `default_permission="allow"` in production (should be `"ask"` or `"deny"`)
- Forgetting that `on_permission_request` is required when permission resolves to `"ask"` — without it, `PermissionDeniedError` is raised
- Using `"fs.*"` when you mean `"fs.write_file"` — wildcards match ALL operations in a skill

## Related Examples
- [01-getting-started](../01-getting-started/) — basic setup
- [04-mcp-server](../04-mcp-server/) — permissions in an MCP server context
