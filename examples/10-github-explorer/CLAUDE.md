# GitHub Explorer Example

## What This Demonstrates
Combining an OpenAPI skill (GitHub) with a custom skill (analysis) in a multi-step Code Mode workflow.

## Key Patterns

```python
from helm import Helm, HelmOptions, openapi
from analysis_skill import analysis

# Register both skills on one agent
github = openapi(spec_path, name="github", headers=headers, default_permission="allow")
agent = Helm(HelmOptions(default_permission="allow"))
agent.use(github).use(analysis())

# Combined discovery
all_ops = agent.search("")
github_ops = [r for r in all_ops if r.skill == "github"]
analysis_ops = [r for r in all_ops if r.skill == "analysis"]

# Multi-step: search → fetch → analyze → report
search = await agent.call("github.search_repos", {"query": {"q": "topic", "per_page": "5"}})
for item in search["data"]["items"]:
    details = await agent.call("github.get_repo", {"owner": owner, "repo": name})
    score = await agent.call("analysis.health_score", {
        "stars": details["data"]["stargazers_count"],
        "forks": details["data"]["forks_count"],
        "open_issues": details["data"]["open_issues_count"],
        "days_since_update": days,
    })
report = await agent.call("analysis.format_report", {"repos": repo_analyses})
```

## Key Imports
```python
from helm import Helm, HelmOptions, openapi
from analysis_skill import analysis  # custom skill factory
```

## How to Replicate This Pattern
1. Create a custom skill with `define_skill()` for domain-specific logic
2. Load an API skill with `openapi()`
3. Register both on the same `Helm` instance
4. Use `agent.search("")` to verify combined operation count
5. Chain API calls + custom calls in a multi-step workflow

## Common Mistakes
- Mixing up skill namespaces — `github.get_repo` vs `analysis.health_score`
- Passing wrong types to custom skill handlers — health_score expects ints, not strings
- Forgetting that `openapi()` handlers return `{"status": ..., "data": ...}` while custom handlers return their own format
- Not handling the case where search returns fewer results than expected

## Related Examples
- [06-custom-skills](../06-custom-skills/) — custom skill basics
- [08-github-openapi](../08-github-openapi/) — GitHub API setup
- [09-github-code-mode](../09-github-code-mode/) — Code Mode workflows without custom skills
