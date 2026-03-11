"""GitHub OpenAPI — use the GitHub REST API through fairlead's openapi() factory."""

import asyncio
import os
from pathlib import Path

from fairlead import Fairlead, FairleadOptions, openapi


async def main() -> None:
    # Build headers — GitHub requires User-Agent; token is optional
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "fairlead-python-examples",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
        print("(Using GITHUB_TOKEN for authentication)\n")
    else:
        print("(No GITHUB_TOKEN set — using unauthenticated access, 60 req/hr)\n")

    # Load curated GitHub spec and create the skill
    spec_path = str(Path(__file__).parent / ".." / "shared" / "github_spec.json")
    github = openapi(spec_path, name="github", headers=headers, default_permission="allow")

    agent = Fairlead(FairleadOptions(default_permission="allow"))
    agent.use(github)

    # -- Discover all operations -------------------------------------------
    print("=== All GitHub Operations ===")
    results = agent.search("")
    print(f"Found {len(results)} operations:\n")
    for r in results:
        print(f"  {r.qualified_name} {r.signature}")

    # -- Search by category ------------------------------------------------
    print("\n=== Search for 'repo' operations ===")
    for r in agent.search("repo"):
        print(f"  {r.qualified_name}: {r.description}")

    print("\n=== Search for 'issue' operations ===")
    for r in agent.search("issue"):
        print(f"  {r.qualified_name}: {r.description}")

    # -- Call endpoints ----------------------------------------------------
    print("\n=== Get User: octocat ===")
    user = await agent.call("github.get_user", {"username": "octocat"})
    print(f"  {user['data']['login']}: {user['data']['name']}")
    print(f"  Public repos: {user['data']['public_repos']}, Followers: {user['data']['followers']}")

    print("\n=== Search Repos: 'python web framework' ===")
    result = await agent.call(
        "github.search_repos",
        {"query": {"q": "python+web+framework", "sort": "stars", "per_page": "5"}},
    )
    for repo in result["data"]["items"][:5]:
        print(f"  {repo['full_name']} ({repo['stargazers_count']:,} stars)")

    print("\n=== Get Repo: python/cpython ===")
    repo = await agent.call("github.get_repo", {"owner": "python", "repo": "cpython"})
    print(f"  {repo['data']['full_name']}: {repo['data']['description']}")
    print(f"  Stars: {repo['data']['stargazers_count']:,}, Forks: {repo['data']['forks_count']:,}")

    print("\n=== Rate Limit ===")
    limit = await agent.call("github.get_rate_limit")
    core = limit["data"]["resources"]["core"]
    print(f"  {core['remaining']}/{core['limit']} requests remaining")


if __name__ == "__main__":
    asyncio.run(main())
