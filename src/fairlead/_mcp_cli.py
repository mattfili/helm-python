from __future__ import annotations

import asyncio

from fairlead._fairlead import Fairlead
from fairlead._mcp_server import serve
from fairlead._types import FairleadOptions
from fairlead.skills._edit import edit
from fairlead.skills._fs import fs
from fairlead.skills._git import git
from fairlead.skills._grep import grep
from fairlead.skills._http import http
from fairlead.skills._shell import shell


def main() -> None:
    agent = Fairlead(FairleadOptions(default_permission="allow"))
    agent.use(fs())
    agent.use(git())
    agent.use(grep())
    agent.use(edit())
    agent.use(http())
    agent.use(shell())
    asyncio.run(serve(agent))


if __name__ == "__main__":
    main()
