"""Code Mode — chain typed operations with branching, looping, and variables."""

import asyncio

from fairlead import Fairlead, FairleadOptions, fs, git, grep


async def main() -> None:
    agent = Fairlead(FairleadOptions(default_permission="allow"))
    agent.use(fs()).use(git()).use(grep())

    # -- Scenario 1: Simple Chain ------------------------------------------
    # Read this file, count lines, then search for a pattern in it.
    print("=== Scenario 1: Simple Chain ===")

    content = await agent.call("fs.read_file", {"path": "pyproject.toml"})
    line_count = len(content["content"].splitlines())
    print(f"pyproject.toml has {line_count} lines")

    matches = await agent.call("grep.search", {"pattern": "Scenario"})
    print(f"Found 'Scenario' in {len(matches['matches'])} locations")

    # -- Scenario 2: Conditional Logic -------------------------------------
    # Check git status, then take action based on what we find.
    print("\n=== Scenario 2: Conditional Logic ===")

    status = await agent.call("git.status")
    print(f"Branch: {status.branch}")

    if status.untracked:
        print(f"Found {len(status.untracked)} untracked files:")
        for f in status.untracked:
            print(f"  - {f}")
    else:
        print("Working tree is clean (no untracked files)")

    if status.staged:
        print(f"Staged changes: {len(status.staged)} files")
    else:
        print("Nothing staged for commit")

    # -- Scenario 3: Loop + Batch ------------------------------------------
    # List directory, stat each file, build a size report.
    print("\n=== Scenario 3: Loop + Batch ===")

    listing = await agent.call("fs.readdir", {"path": "."})
    report: list[tuple[str, int]] = []

    for entry in listing["entries"]:
        if entry.is_file:
            stat = await agent.call("fs.stat", {"path": entry.path})
            report.append((entry.name, stat.size))

    report.sort(key=lambda x: x[1], reverse=True)
    print("Files by size:")
    for name, size in report:
        print(f"  {name}: {size:,} bytes")

    # -- Why This Matters --------------------------------------------------
    # All three scenarios use the same `.call()` interface that MCP clients
    # use. Code Mode means your agent logic is real Python — with types,
    # control flow, and testability — not prompt engineering.


if __name__ == "__main__":
    asyncio.run(main())
