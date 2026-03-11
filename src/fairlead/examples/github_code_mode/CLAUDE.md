# GitHub Code Mode Example

## What This Demonstrates
Multi-step Code Mode workflows against a real API — search + aggregate, conditional branching, and data comparison.

## Key Patterns

```python
# Pattern 1: Search → fetch details → rank
search = await agent.call("github.search_repos", {"query": {"q": "topic", "per_page": "5"}})
ranked = []
for item in search["data"]["items"]:
    details = await agent.call("github.get_repo", {"owner": item["owner"]["login"], "repo": item["name"]})
    ranked.append(details["data"])
ranked.sort(key=lambda r: r["stargazers_count"], reverse=True)

# Pattern 2: List → filter → drill down
org_repos = await agent.call("github.list_org_repos", {"org": "pallets", "query": {"per_page": "5"}})
for repo in org_repos["data"]:
    if repo["open_issues_count"] > 0:
        issues = await agent.call("github.list_repo_issues", {
            "owner": "pallets", "repo": repo["name"],
            "query": {"state": "open", "per_page": "3"},
        })

# Pattern 3: Parallel fetch + compare
for owner, name in [("pallets", "flask"), ("django", "django")]:
    repo = await agent.call("github.get_repo", {"owner": owner, "repo": name})
    langs = await agent.call("github.list_repo_languages", {"owner": owner, "repo": name})
    contribs = await agent.call("github.list_repo_contributors", {"owner": owner, "repo": name, "query": {"per_page": "3"}})
```

## Key Imports
```python
from fairlead import Fairlead, FairleadOptions, openapi
```

## How to Replicate This Pattern
1. Load a real API via `openapi()` with appropriate headers
2. Use `agent.call()` in loops to fetch details for each search result
3. Store results in Python data structures (lists, dicts)
4. Use conditionals to filter and drill down
5. Aggregate and format results with standard Python

## Common Mistakes
- Exceeding rate limits — this example makes ~15-20 calls; set `GITHUB_TOKEN` for production use
- Forgetting that query param values must be strings (`"per_page": "5"`)
- Spaces in query values — use `+` or `%20` (`"q": "python+web"` not `"q": "python web"`)
- Accessing search results directly instead of via `data["items"]`
- Not handling empty results in conditional branches

## Related Examples
- [03-code-mode](../03-code-mode/) — Code Mode basics with local file operations
- [08-github-openapi](../08-github-openapi/) — GitHub API setup and discovery
- [10-github-explorer](../10-github-explorer/) — combines Code Mode with custom analysis skills
