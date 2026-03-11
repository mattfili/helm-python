"""GitHub Explorer — combine OpenAPI skill + custom skill + Code Mode into a multi-step workflow."""

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from fairlead import Fairlead, FairleadOptions, openapi

from .analysis_skill import analysis


async def main() -> None:
    # -- Register both skills ----------------------------------------------
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

    spec_path = str(Path(__file__).parent / ".." / "shared" / "github_spec.json")
    github = openapi(spec_path, name="github", headers=headers, default_permission="allow")

    agent = Fairlead(FairleadOptions(default_permission="allow"))
    agent.use(github).use(analysis())

    # -- Show combined discovery -------------------------------------------
    all_ops = agent.search("")
    github_ops = [r for r in all_ops if r.skill == "github"]
    analysis_ops = [r for r in all_ops if r.skill == "analysis"]
    print(f"Registered {len(github_ops)} GitHub ops + {len(analysis_ops)} analysis ops\n")

    # -- Search repos by topic ---------------------------------------------
    print('=== Exploring "python async" repos ===\n')
    search = await agent.call(
        "github.search_repos",
        {"query": {"q": "python+async", "sort": "stars", "per_page": "5"}},
    )

    # -- Fetch details + compute health scores -----------------------------
    repo_analyses: list[dict] = []
    now = datetime.now(timezone.utc)

    for item in search["data"]["items"][:5]:
        owner = item["owner"]["login"]
        name = item["name"]

        # Fetch full details
        details = await agent.call("github.get_repo", {"owner": owner, "repo": name})
        d = details["data"]

        # Fetch languages
        langs = await agent.call("github.list_repo_languages", {"owner": owner, "repo": name})
        lang_data = langs["data"]
        total_bytes = sum(lang_data.values()) if lang_data else 1
        top_langs = sorted(lang_data.items(), key=lambda x: x[1], reverse=True)[:3]
        lang_str = ", ".join(f"{l}: {b * 100 / total_bytes:.0f}%" for l, b in top_langs)

        # Compute days since last update
        updated = datetime.fromisoformat(d["updated_at"].replace("Z", "+00:00"))
        days_since = (now - updated).days

        # Compute health score via custom skill
        score = await agent.call(
            "analysis.health_score",
            {
                "stars": d["stargazers_count"],
                "forks": d["forks_count"],
                "open_issues": d["open_issues_count"],
                "days_since_update": days_since,
            },
        )

        repo_analyses.append({
            "name": d["full_name"],
            "stars": d["stargazers_count"],
            "forks": d["forks_count"],
            "languages": lang_str,
            "health_score": score,
        })

    # -- Generate report via custom skill ----------------------------------
    report = await agent.call("analysis.format_report", {"repos": repo_analyses})
    print(report["report"])

    # -- Show health score breakdown for top repo --------------------------
    if repo_analyses:
        top = max(repo_analyses, key=lambda r: r["health_score"]["total"])
        print(f"\nHealthiest repo: {top['name']}")
        breakdown = top["health_score"]["breakdown"]
        for category, value in breakdown.items():
            max_val = {"popularity": 40, "community": 25, "maintenance": 20, "issue_health": 15}[category]
            print(f"  {category:15s}: {value}/{max_val}")


if __name__ == "__main__":
    asyncio.run(main())
