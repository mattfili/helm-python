import asyncio

from helm import HelmOptions, create_helm
from helm.skills import fs, git


async def main() -> None:
    agent = (
        create_helm(HelmOptions(default_permission="allow"))
        .use(fs())
        .use(git())
    )

    result = await agent.fs.read_file("pyproject.toml")
    print("=== pyproject.toml ===")
    print(result["content"])

    status = await agent.git.status()
    print("\n=== git status ===")
    print(f"Branch: {status.branch}")
    print(f"Untracked: {status.untracked}")

    results = agent.search("file")
    print(f"\n=== search 'file' ({len(results)} results) ===")
    for r in results[:5]:
        print(f"  {r.qualified_name}: {r.description}")


if __name__ == "__main__":
    asyncio.run(main())
