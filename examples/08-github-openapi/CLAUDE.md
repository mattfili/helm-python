# GitHub OpenAPI Example

## What This Demonstrates
Using `openapi()` with a real, production API (GitHub) — including auth headers, large operation discovery, and typed API calls.

## Key Patterns

```python
from helm import Helm, HelmOptions, openapi

# GitHub requires User-Agent; token is optional
headers = {"Accept": "application/vnd.github+json", "User-Agent": "helm-python-examples"}
token = os.environ.get("GITHUB_TOKEN")
if token:
    headers["Authorization"] = f"Bearer {token}"

# Load curated spec (18 endpoints, all GET-only)
github = openapi(
    str(Path(__file__).parent / ".." / "shared" / "github_spec.json"),
    name="github",
    headers=headers,
    default_permission="allow",
)

agent = Helm(HelmOptions(default_permission="allow"))
agent.use(github)

# Discover all 18 operations
results = agent.search("")

# Search by category
agent.search("repo")   # repo-related operations
agent.search("issue")  # issue-related operations

# Call endpoints — path params as kwargs, query params in query dict
user = await agent.call("github.get_user", {"username": "octocat"})
repos = await agent.call("github.search_repos", {"query": {"q": "python", "sort": "stars"}})
# Search results are in data["items"], not data directly
for repo in repos["data"]["items"]:
    print(repo["full_name"])
```

## Key Imports
```python
from helm import Helm, HelmOptions, openapi
```

## How to Replicate This Pattern
1. Get or create an OpenAPI 3.x spec for your target API
2. Build a headers dict with required auth/identification headers
3. Call `openapi(spec, name="...", headers=headers)` to create the skill
4. Register with `agent.use(skill)`
5. Use `agent.search("")` to discover all operations
6. Call operations with path params as kwargs, query params in `{"query": {...}}`

## Common Mistakes
- Forgetting `User-Agent` header — GitHub returns 403 without it
- Using integers for query param values — use strings (`"per_page": "5"` not `"per_page": 5`)
- Spaces in query values — use `+` or `%20` (`"q": "python+web"` not `"q": "python web"`)
- Accessing search results as `data` instead of `data["items"]` — GitHub wraps search results
- Not checking `GITHUB_TOKEN` — unauthenticated access is limited to 60 req/hr

## Related Examples
- [07-openapi-skill](../07-openapi-skill/) — simpler OpenAPI example with Petstore
- [09-github-code-mode](../09-github-code-mode/) — chain GitHub operations with Code Mode
- [10-github-explorer](../10-github-explorer/) — combine GitHub API with custom analysis skills
