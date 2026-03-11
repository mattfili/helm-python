"""Getting Started with fairlead — typed operations for AI agents."""

import asyncio

from fairlead import Fairlead, FairleadOptions, fs, git, grep


async def main() -> None:
    # 1. Create a Fairlead instance with permissive defaults (fine for scripts)
    agent = Fairlead(FairleadOptions(default_permission="allow"))

    # 2. Register built-in skills
    agent.use(fs()).use(git()).use(grep())

    # 3. Call typed operations via attribute access
    #    Every operation is async and returns structured data.

    # Read a file — returns {"content": "..."}
    result = await agent.fs.read_file(path="pyproject.toml")
    lines = result["content"].splitlines()
    print(f"pyproject.toml has {len(lines)} lines")

    # Get git status — returns a GitStatus dataclass
    status = await agent.git.status()
    print(f"On branch: {status.branch}")
    print(f"Untracked files: {len(status.untracked)}")

    # List the current directory — returns {"entries": [DirEntry, ...]}
    listing = await agent.fs.readdir(path=".")
    names = [e.name for e in listing["entries"]]
    print(f"Files here: {', '.join(sorted(names))}")

    # 4. Discover operations with search()
    print("\n--- Searching for 'file' operations ---")
    results = agent.search("file")
    for r in results[:5]:
        print(f"  {r.qualified_name}: {r.description}")

    print("\n--- Searching for 'git' operations ---")
    results = agent.search("git")
    for r in results[:5]:
        print(f"  {r.qualified_name} {r.signature}")


if __name__ == "__main__":
    asyncio.run(main())
