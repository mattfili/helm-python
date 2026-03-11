"""GitHub MCP Server — expose the GitHub API to Claude Desktop with permissions."""

import asyncio
import os
from pathlib import Path

from helm import Helm, HelmOptions, openapi, serve


async def main() -> None:
    # Build headers — GitHub requires User-Agent; token is optional
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "helm-python-examples",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Load curated GitHub spec (18 GET-only endpoints)
    spec_path = str(Path(__file__).parent / ".." / "shared" / "github_spec.json")
    github = openapi(spec_path, name="github", headers=headers, default_permission="allow")

    # Configure permissions — allow all GitHub ops, deny everything else
    agent = Helm(HelmOptions(
        permissions={"github.*": "allow"},
        default_permission="deny",
    ))
    agent.use(github)

    # Start the MCP server — Claude Desktop can now search and call GitHub endpoints
    await serve(agent)


if __name__ == "__main__":
    asyncio.run(main())
