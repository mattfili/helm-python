"""Permission system — exact match, wildcard, defaults, and denied errors."""

import asyncio

from helm import (
    Helm, HelmOptions, PermissionDeniedError,
    define_skill, OperationDef,
    fs, git,
)


async def main() -> None:
    # Create a custom skill to demonstrate global default (built-in ops
    # all have their own defaults, so the global default never triggers)
    async def ping() -> str:
        return "pong"

    demo = define_skill(
        name="demo",
        description="Demo skill with no operation-level default",
        operations={
            "ping": OperationDef(
                description="Simple ping",
                handler=ping,
                # NOTE: no default_permission — falls through to global default
            ),
        },
    )

    # Configure permissions with a mix of exact rules, wildcards, and defaults
    agent = Helm(HelmOptions(
        permissions={
            "fs.read_file": "allow",     # exact: allow reading files
            "fs.write_file": "deny",     # exact: block writing files
            "git.*": "allow",            # wildcard: allow all git operations
        },
        default_permission="deny",       # global: deny everything else
    ))
    agent.use(fs()).use(git()).use(demo)

    # --- Step 1: Exact match in policy ---
    result = await agent.fs.read_file(path="main.py")
    print(f"fs.read_file: OK ({len(result['content'])} bytes)")

    # --- Step 1: Exact match "deny" ---
    try:
        await agent.fs.write_file(path="/tmp/test.txt", content="hello")
        print("fs.write_file: OK")
    except PermissionDeniedError as e:
        print(f"fs.write_file: DENIED ({e.qualified_name})")

    # --- Step 2: Wildcard match ---
    status = await agent.git.status()
    print(f"git.status: OK (branch={status.branch})")

    log = await agent.git.log()
    print(f"git.log: OK ({len(log['commits'])} commits)")

    # --- Step 3: Operation default ---
    # fs.readdir has default_permission="allow" in the skill definition,
    # so even without a policy entry, it resolves to "allow"
    listing = await agent.fs.readdir(path=".")
    names = [e.name for e in listing["entries"]]
    print(f"fs.readdir: OK via operation default ({len(names)} entries)")

    # --- Step 4: Global default ---
    # demo.ping has no operation default and no policy entry,
    # so it falls through to the global default ("deny")
    try:
        await agent.demo.ping()
        print("demo.ping: OK")
    except PermissionDeniedError as e:
        print(f"demo.ping: DENIED by global default ({e.qualified_name})")

    # --- Summary ---
    print("\n--- Permission Resolution Order ---")
    print("1. Exact match in policy   (fs.read_file -> allow, fs.write_file -> deny)")
    print("2. Wildcard match          (git.* -> allow)")
    print("3. Operation default       (fs.readdir -> allow, from skill definition)")
    print("4. Global default          (demo.ping -> deny, no other rule matched)")


if __name__ == "__main__":
    asyncio.run(main())
