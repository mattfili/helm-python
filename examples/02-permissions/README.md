# 02 — Permissions

Deep dive into helm's permission system. Shows exact match rules, wildcard patterns, operation defaults, global defaults, `PermissionDeniedError`, and the `on_permission_request` callback for interactive approval.

## What You'll Learn

- Permission resolution order (exact > wildcard > operation default > global default)
- Setting per-operation and wildcard permissions in `HelmOptions`
- Handling `PermissionDeniedError`
- Implementing `on_permission_request` for interactive approval

## Run It

```bash
pip install -e ../..
python main.py          # non-interactive permission demo
python interactive.py   # interactive approval callback
```

## Permission Resolution Order

1. **Exact match**: `"fs.write_file": "deny"` — matches only `fs.write_file`
2. **Wildcard**: `"git.*": "allow"` — matches all git operations
3. **Operation default**: Each operation defines its own default (e.g., `fs.read_file` defaults to `"allow"`)
4. **Global default**: `HelmOptions(default_permission="ask")` — fallback for everything else
