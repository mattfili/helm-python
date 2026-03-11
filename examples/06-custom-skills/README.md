# 06 — Custom Skills

Define domain-specific skills with `define_skill()` and `OperationDef`. Shows sync and async handlers, custom tags, signatures, and composing custom skills alongside built-ins.

## What You'll Learn

- Creating skills with `define_skill()`
- Defining operations with `OperationDef`
- Writing sync and async handlers
- Adding tags and signatures for discoverability
- Composing custom skills with built-in ones

## Run It

```bash
pip install -e ../..
python main.py
```

## When to Use Custom Skills

Custom skills are useful when you want to:
- Wrap a domain-specific API (weather, database, Slack, etc.)
- Create higher-level abstractions over built-in operations
- Add business logic with proper type signatures
- Make operations discoverable via `search()`
