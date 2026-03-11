"""GitHub Code Mode — chain typed GitHub API calls with branching, looping, and aggregation."""

import asyncio
import os
from pathlib import Path

from helm import Helm, HelmOptions, openapi


def _github_skill() -> object:
    """Load the GitHub OpenAPI skill with optional auth."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "helm-python-examples",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    spec_path = str(Path(__file__).parent / ".." / "shared" / "github_spec.json")
    return openapi(spec_path, name="github", headers=headers, default_permission="allow")


async def main() -> None:
    agent = Helm(HelmOptions(default_permission="allow"))
    agent.use(_github_skill())

    # ── Scenario 1: Search + Rank ────────────────────────────────────
    # Search repos, fetch full details for each, rank by stars.
    print("=== Scenario 1: Search + Rank ===")
    print('Searching "machine learning python" repos...\n')

    search = await agent.call(
        "github.search_repos",
        {"query": {"q": "machine+learning+python", "sort": "stars", "per_page": "5"}},
    )

    ranked: list[dict] = []
    for item in search["data"]["items"][:5]:
        details = await agent.call(
            "github.get_repo", {"owner": item["owner"]["login"], "repo": item["name"]}
        )
        d = details["data"]
        ranked.append({
            "name": d["full_name"],
            "stars": d["stargazers_count"],
            "forks": d["forks_count"],
            "open_issues": d["open_issues_count"],
            "language": d["language"],
        })

    ranked.sort(key=lambda r: r["stars"], reverse=True)
    for i, r in enumerate(ranked, 1):
        print(f"  {i}. {r['name']}")
        print(f"     {r['stars']:,} stars, {r['forks']:,} forks, {r['open_issues']} open issues")
        print(f"     Language: {r['language']}")

    # ── Scenario 2: Org Repos + Issue Scan ───────────────────────────
    # List pallets org repos, find those with open issues, list them.
    print("\n=== Scenario 2: Org Repos + Issue Scan ===")
    print("Scanning pallets org for repos with open issues...\n")

    org_repos = await agent.call(
        "github.list_org_repos", {"org": "pallets", "query": {"per_page": "5"}}
    )

    for repo in org_repos["data"][:5]:
        if repo["open_issues_count"] > 0:
            print(f"  {repo['name']} ({repo['open_issues_count']} open issues):")
            issues = await agent.call(
                "github.list_repo_issues",
                {
                    "owner": "pallets",
                    "repo": repo["name"],
                    "query": {"state": "open", "per_page": "3"},
                },
            )
            for issue in issues["data"][:3]:
                labels = ", ".join(l["name"] for l in issue.get("labels", []))
                label_str = f" [{labels}]" if labels else ""
                print(f"    #{issue['number']}: {issue['title']}{label_str}")

    # ── Scenario 3: Compare Two Repos ────────────────────────────────
    # Fetch Flask vs Django stats side by side.
    print("\n=== Scenario 3: Compare Two Repos ===")
    print("Comparing Flask vs Django...\n")

    repos_to_compare = [("pallets", "flask"), ("django", "django")]
    comparison: list[dict] = []

    for owner, name in repos_to_compare:
        repo = await agent.call("github.get_repo", {"owner": owner, "repo": name})
        langs = await agent.call("github.list_repo_languages", {"owner": owner, "repo": name})
        contribs = await agent.call(
            "github.list_repo_contributors",
            {"owner": owner, "repo": name, "query": {"per_page": "3"}},
        )

        d = repo["data"]
        top_contribs = [c["login"] for c in contribs["data"][:3]]

        # Compute language percentages
        lang_data = langs["data"]
        total_bytes = sum(lang_data.values()) if lang_data else 1
        top_langs = sorted(lang_data.items(), key=lambda x: x[1], reverse=True)[:3]
        lang_pcts = [f"{l}: {b * 100 / total_bytes:.0f}%" for l, b in top_langs]

        comparison.append({
            "name": d["full_name"],
            "stars": d["stargazers_count"],
            "forks": d["forks_count"],
            "open_issues": d["open_issues_count"],
            "languages": ", ".join(lang_pcts),
            "top_contributors": ", ".join(top_contribs),
        })

    # Print side by side
    labels = ["Stars", "Forks", "Open Issues", "Languages", "Top Contributors"]
    keys = ["stars", "forks", "open_issues", "languages", "top_contributors"]
    header = f"  {'':20s} {comparison[0]['name']:>25s}   {comparison[1]['name']:>25s}"
    print(header)
    print(f"  {'─' * 20} {'─' * 25}   {'─' * 25}")
    for label, key in zip(labels, keys):
        v0 = comparison[0][key]
        v1 = comparison[1][key]
        v0_str = f"{v0:,}" if isinstance(v0, int) else str(v0)
        v1_str = f"{v1:,}" if isinstance(v1, int) else str(v1)
        print(f"  {label:20s} {v0_str:>25s}   {v1_str:>25s}")


if __name__ == "__main__":
    asyncio.run(main())
