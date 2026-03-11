# 08 — GitHub OpenAPI

Use the real GitHub REST API through fairlead's `openapi()` factory. A curated 18-endpoint OpenAPI spec gives you typed access to users, repos, issues, and search — all auto-discovered via `search()`.

## What You'll Learn

- Loading a real-world OpenAPI spec with `openapi()`
- Passing authentication headers (optional `GITHUB_TOKEN`)
- Discovering operations with `search("")` and `search("topic")`
- Calling real API endpoints with typed results

## Run It

```bash
pip install -e ../..
python main.py
```

Set `GITHUB_TOKEN` for 5,000 req/hr (vs 60 unauthenticated):

```bash
export GITHUB_TOKEN=ghp_your_token_here
python main.py
```

## How It Works

The curated spec at `../shared/github_spec.json` contains 18 GET-only endpoints from the GitHub API. The `openapi()` factory turns each into a fairlead operation:

- `GET /users/{username}` → `github.get_user`
- `GET /search/repositories` → `github.search_repos`
- `GET /repos/{owner}/{repo}` → `github.get_repo`
- ... and 15 more

All endpoints work without authentication on public data. GitHub requires a `User-Agent` header, which the example sets automatically.
