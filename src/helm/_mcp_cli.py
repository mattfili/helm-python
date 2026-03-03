from __future__ import annotations

import asyncio

from helm._helm import Helm
from helm._mcp_server import serve
from helm._types import HelmOptions
from helm.skills._edit import edit
from helm.skills._fs import fs
from helm.skills._git import git
from helm.skills._grep import grep
from helm.skills._http import http
from helm.skills._shell import shell


def main() -> None:
    helm = Helm(HelmOptions(default_permission="allow"))
    helm.use(fs())
    helm.use(git())
    helm.use(grep())
    helm.use(edit())
    helm.use(http())
    helm.use(shell())
    asyncio.run(serve(helm))


if __name__ == "__main__":
    main()
