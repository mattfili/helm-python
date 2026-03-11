# 03 — Code Mode

The core differentiator. Code Mode uses `agent.call()` to chain operations with branching, looping, and variable assignment over typed results — turning helm into a programmable agent runtime.

## What You'll Learn

- Using `agent.call()` for dynamic operation dispatch
- Chaining calls with intermediate variables
- Conditional logic based on typed results
- Looping over results to batch operations

## Run It

```bash
pip install -e ../..
python main.py
```

## Why Code Mode?

Instead of sending natural-language instructions and hoping the agent does the right thing, Code Mode lets you write **deterministic Python** that calls typed operations. You get:

- **Type safety** — results are dataclasses, not strings to parse
- **Control flow** — real `if/else`, `for` loops, exception handling
- **Composability** — build complex workflows from simple operations
- **Testability** — unit test your agent logic like any other code
