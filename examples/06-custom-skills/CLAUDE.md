# Custom Skills Example

## What This Demonstrates
Defining domain-specific skills with `define_skill()` and `OperationDef`, with sync/async handlers, tags, and signatures.

## Key Patterns

```python
from helm import define_skill, OperationDef

# Async handler
async def get_weather(city: str) -> dict:
    return {"city": city, "temp_f": 72, "condition": "sunny"}

# Sync handler (also works)
def convert_temp(temp_f: float) -> dict:
    return {"celsius": round((temp_f - 32) * 5 / 9, 1)}

weather = define_skill(
    name="weather",
    description="Weather operations",
    operations={
        "get": OperationDef(
            description="Get current weather for a city",
            handler=get_weather,
            signature="(city: str) -> dict",
            tags=["weather", "temperature", "forecast"],
            default_permission="allow",
        ),
        "convert": OperationDef(
            description="Convert Fahrenheit to Celsius",
            handler=convert_temp,
            signature="(temp_f: float) -> dict",
            tags=["weather", "convert", "temperature"],
            default_permission="allow",
        ),
    },
)

agent.use(weather)
```

## Key Imports
```python
from helm import Helm, HelmOptions, define_skill, OperationDef
```

## How to Replicate This Pattern
1. Write handler functions (sync or async) that return typed data
2. Create `OperationDef` for each operation with description, handler, signature, and tags
3. Call `define_skill(name=..., description=..., operations=...)` to create the skill
4. Register with `agent.use(skill)`

## Common Mistakes
- Returning non-serializable objects from handlers (use dicts or dataclasses)
- Forgetting `default_permission` — operations default to the global setting
- Not adding tags — operations without tags are harder to discover via `search()`
- Naming collisions — skill names must be unique per Helm instance

## Related Examples
- [01-getting-started](../01-getting-started/) — using built-in skills
- [07-openapi-skill](../07-openapi-skill/) — auto-generating skills from OpenAPI specs
