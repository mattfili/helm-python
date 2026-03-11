# 07 — OpenAPI Skill

Turn any OpenAPI 3.x spec into a helm skill with the `openapi()` factory. Load from a URL or local file, discover endpoints via `search()`, and call them with typed results.

## What You'll Learn

- Creating skills from OpenAPI specs with `openapi()`
- Loading specs from local files
- Discovering auto-generated operations via `search()`
- Calling API endpoints through helm's typed interface

## Run It

```bash
pip install -e ../..
python main.py
```

## How It Works

The `openapi()` factory:
1. Parses the OpenAPI spec (JSON or YAML)
2. Creates an operation for each endpoint (GET /pets -> `list_pets`)
3. Generates signatures from path/query/body parameters
4. Sets up HTTP handlers that make real API calls

Each operation gets tags from the spec plus the HTTP method, making them discoverable via `search()`.
