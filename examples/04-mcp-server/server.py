"""MCP Server — expose helm operations to Claude Desktop and other MCP clients."""

import asyncio

from helm import Helm, HelmOptions, serve, fs, git, grep, edit, http, shell


async def main() -> None:
    # Configure which skills to expose and their permissions.
    # In production, use tighter permissions — "allow" here for simplicity.
    agent = Helm(HelmOptions(default_permission="allow"))

    # Register the skills you want available via MCP.
    # Only registered skills are exposed — skip any you don't need.
    agent.use(fs())
    agent.use(git())
    agent.use(grep())
    agent.use(edit())
    agent.use(http())
    agent.use(shell())

    # Start the MCP server. It reads JSON-RPC from stdin and writes to stdout.
    # MCP clients see exactly 2 tools:
    #   search(query) — discover operations
    #   call(name, args) — invoke an operation
    await serve(agent)


if __name__ == "__main__":
    asyncio.run(main())
