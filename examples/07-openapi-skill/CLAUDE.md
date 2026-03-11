# OpenAPI Skill Example

## What This Demonstrates
Auto-generating helm skills from OpenAPI 3.x specs with the `openapi()` factory.

## Key Patterns

```python
from helm import openapi

# From a local file
petstore = openapi(
    "petstore_spec.json",
    name="petstore",
    default_permission="allow",
)

# From a URL
api = openapi(
    "https://api.example.com/openapi.json",
    name="example",
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer token"},
    default_permission="allow",
)

agent.use(petstore)
results = agent.search("pets")  # discovers auto-generated operations
data = await agent.call("petstore.list_pets", {"query": {"limit": "10"}})
```

## Key Imports
```python
from helm import Helm, HelmOptions, openapi
```

## How to Replicate This Pattern
1. Get an OpenAPI 3.x spec (JSON or YAML file/URL)
2. Call `openapi(spec, name="...", ...)` to create a skill
3. Register with `agent.use(skill)`
4. Use `agent.search()` to discover auto-generated operation names
5. Call operations with `agent.call()` or attribute access

## Common Mistakes
- Not installing PyYAML for YAML specs (`pip install pyyaml`)
- Forgetting `base_url` when the spec doesn't include servers
- Using wrong parameter format — path params are kwargs, query params go in `query` dict
- Expecting operation names to match paths — they're derived from `operationId` or slugified

## Related Examples
- [06-custom-skills](../06-custom-skills/) — manual skill definition (more control)
- [01-getting-started](../01-getting-started/) — basic skill registration
