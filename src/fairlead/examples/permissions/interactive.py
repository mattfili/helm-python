"""Interactive permission approval with on_permission_request callback."""

import asyncio

from fairlead import Fairlead, FairleadOptions, PermissionDeniedError, fs, git


def approve(operation: str, args: list) -> bool:
    """Prompt the user to approve or deny an operation."""
    print(f"\n  Operation: {operation}")
    print(f"  Arguments: {args}")
    answer = input("  Allow? [y/n] ").strip().lower()
    return answer == "y"


async def main() -> None:
    # Use "ask" as default — the callback decides at runtime
    agent = Fairlead(FairleadOptions(
        default_permission="ask",
        on_permission_request=approve,
    ))
    agent.use(fs()).use(git())

    print("This demo will ask you to approve each operation.\n")

    # Each of these will trigger the approval callback
    try:
        result = await agent.fs.read_file(path="interactive.py")
        print(f"  -> Read {len(result['content'])} bytes\n")
    except PermissionDeniedError:
        print("  -> Denied by user\n")

    try:
        status = await agent.git.status()
        print(f"  -> Branch: {status.branch}\n")
    except PermissionDeniedError:
        print("  -> Denied by user\n")

    try:
        listing = await agent.fs.readdir(path=".")
        names = [e.name for e in listing["entries"]]
        print(f"  -> Files: {', '.join(sorted(names))}\n")
    except PermissionDeniedError:
        print("  -> Denied by user\n")


if __name__ == "__main__":
    asyncio.run(main())
