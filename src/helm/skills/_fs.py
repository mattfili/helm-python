from __future__ import annotations

import asyncio
import fnmatch
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from helm._skill import define_skill
from helm._types import OperationDef, Skill


@dataclass(frozen=True)
class DirEntry:
    name: str
    path: str
    is_file: bool
    is_directory: bool


@dataclass(frozen=True)
class StatResult:
    size: int
    is_file: bool
    is_directory: bool
    modified: str
    created: str


def fs() -> Skill:
    async def read_file(path: str) -> dict[str, str]:
        content = await asyncio.to_thread(Path(path).read_text, encoding="utf-8")
        return {"content": content}

    async def write_file(path: str, content: str) -> None:
        await asyncio.to_thread(Path(path).write_text, content, encoding="utf-8")

    async def readdir(
        path: str, opts: dict[str, str] | None = None
    ) -> dict[str, list[DirEntry]]:
        def _readdir() -> list[DirEntry]:
            p = Path(path)
            entries: list[DirEntry] = []
            for item in p.iterdir():
                entries.append(
                    DirEntry(
                        name=item.name,
                        path=str(item),
                        is_file=item.is_file(),
                        is_directory=item.is_dir(),
                    )
                )

            if opts and opts.get("glob"):
                glob_pattern = opts["glob"]
                entries = [
                    e for e in entries if fnmatch.fnmatch(e.name, glob_pattern)
                ]

            return entries

        entries = await asyncio.to_thread(_readdir)
        return {"entries": entries}

    async def mkdir(path: str) -> None:
        await asyncio.to_thread(Path(path).mkdir, parents=True, exist_ok=True)

    async def stat(path: str) -> StatResult:
        def _stat() -> StatResult:
            p = Path(path)
            s = p.stat()
            from datetime import datetime, timezone

            return StatResult(
                size=s.st_size,
                is_file=p.is_file(),
                is_directory=p.is_dir(),
                modified=datetime.fromtimestamp(s.st_mtime, tz=timezone.utc).isoformat(),
                created=datetime.fromtimestamp(
                    getattr(s, "st_birthtime", s.st_ctime), tz=timezone.utc
                ).isoformat(),
            )

        return await asyncio.to_thread(_stat)

    async def rm(path: str) -> None:
        def _rm() -> None:
            p = Path(path)
            if p.is_dir():
                shutil.rmtree(str(p))
            else:
                p.unlink()

        await asyncio.to_thread(_rm)

    async def rename(old_path: str, new_path: str) -> None:
        await asyncio.to_thread(Path(old_path).rename, new_path)

    async def cwd() -> str:
        return os.getcwd()

    return define_skill(
        name="fs",
        description="File system operations — read_file, write_file, readdir, mkdir, stat, rm, rename, cwd",
        operations={
            "read_file": OperationDef(
                description="Read a file and return its content as a string",
                signature="(path: str) -> dict[str, str]",
                default_permission="allow",
                tags=["file", "read", "cat", "open", "content", "text", "load"],
                handler=read_file,
            ),
            "write_file": OperationDef(
                description="Write content to a file, creating it if it doesn't exist",
                signature="(path: str, content: str) -> None",
                default_permission="ask",
                tags=["file", "write", "save", "create", "overwrite", "put", "output"],
                handler=write_file,
            ),
            "readdir": OperationDef(
                description="List entries in a directory",
                signature="(path: str, opts: dict | None = None) -> dict[str, list[DirEntry]]",
                default_permission="allow",
                tags=["directory", "list", "ls", "dir", "entries", "files", "browse"],
                handler=readdir,
            ),
            "mkdir": OperationDef(
                description="Create a directory, including any parent directories",
                signature="(path: str) -> None",
                default_permission="ask",
                tags=["directory", "create", "mkdir", "folder", "make", "new", "mkdirp"],
                handler=mkdir,
            ),
            "stat": OperationDef(
                description="Get file or directory metadata — size, type, timestamps",
                signature="(path: str) -> StatResult",
                default_permission="allow",
                tags=["file", "stat", "info", "metadata", "size", "exists", "check"],
                handler=stat,
            ),
            "rm": OperationDef(
                description="Remove a file or directory recursively",
                signature="(path: str) -> None",
                default_permission="ask",
                tags=["file", "delete", "remove", "rm", "unlink", "destroy", "clean"],
                handler=rm,
            ),
            "rename": OperationDef(
                description="Rename or move a file or directory",
                signature="(old_path: str, new_path: str) -> None",
                default_permission="ask",
                tags=["file", "rename", "move", "mv"],
                handler=rename,
            ),
            "cwd": OperationDef(
                description="Get the current working directory",
                signature="() -> str",
                default_permission="allow",
                tags=["directory", "cwd", "pwd", "path", "current"],
                handler=cwd,
            ),
        },
    )
