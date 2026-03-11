"""A custom analysis skill — health scoring and report generation for GitHub repos."""

from __future__ import annotations

from fairlead import define_skill, OperationDef, Skill


def health_score(
    stars: int, forks: int, open_issues: int, days_since_update: int
) -> dict[str, object]:
    """Compute a health score (0–100) with breakdown."""
    # Popularity (0–40): log-scale star count
    import math
    pop = min(40, int(math.log10(max(stars, 1) + 1) * 10))

    # Community (0–25): fork-to-star ratio indicates contribution
    fork_ratio = forks / max(stars, 1)
    community = min(25, int(fork_ratio * 100))

    # Maintenance (0–20): penalize stale repos
    if days_since_update <= 7:
        maintenance = 20
    elif days_since_update <= 30:
        maintenance = 15
    elif days_since_update <= 90:
        maintenance = 10
    elif days_since_update <= 365:
        maintenance = 5
    else:
        maintenance = 0

    # Issue health (0–15): some issues are good (active), too many is bad
    issue_ratio = open_issues / max(stars, 1) * 1000
    if issue_ratio < 5:
        issue_health = 15
    elif issue_ratio < 20:
        issue_health = 10
    elif issue_ratio < 50:
        issue_health = 5
    else:
        issue_health = 0

    total = pop + community + maintenance + issue_health

    return {
        "total": total,
        "breakdown": {
            "popularity": pop,
            "community": community,
            "maintenance": maintenance,
            "issue_health": issue_health,
        },
    }


def format_report(repos: list[dict]) -> dict[str, str]:
    """Format a list of repo analysis results into a text report."""
    lines = ["=" * 60, "  GitHub Repository Health Report", "=" * 60, ""]

    for repo in repos:
        score = repo.get("health_score", {})
        total = score.get("total", 0)
        breakdown = score.get("breakdown", {})

        # Score bar: ████░░░░░░ 72/100
        filled = int(total / 5)
        bar = "\u2588" * filled + "\u2591" * (20 - filled)

        lines.append(f"  {repo['name']}")
        lines.append(f"  {bar} {total}/100")
        lines.append(f"    Stars: {repo.get('stars', 0):,}  Forks: {repo.get('forks', 0):,}")
        if repo.get("languages"):
            lines.append(f"    Languages: {repo['languages']}")
        if breakdown:
            parts = [f"{k}: {v}" for k, v in breakdown.items()]
            lines.append(f"    Breakdown: {', '.join(parts)}")
        lines.append("")

    lines.append("=" * 60)
    return {"report": "\n".join(lines)}


def analysis() -> Skill:
    """Create the analysis skill."""
    return define_skill(
        name="analysis",
        description="Repository health scoring and report generation",
        operations={
            "health_score": OperationDef(
                description="Compute a health score (0-100) for a repository",
                handler=health_score,
                signature="(stars: int, forks: int, open_issues: int, days_since_update: int) -> dict",
                tags=["analysis", "health", "score", "repository"],
                default_permission="allow",
            ),
            "format_report": OperationDef(
                description="Format repository analysis results into a text report",
                handler=format_report,
                signature="(repos: list[dict]) -> dict[str, str]",
                tags=["analysis", "report", "format"],
                default_permission="allow",
            ),
        },
    )
