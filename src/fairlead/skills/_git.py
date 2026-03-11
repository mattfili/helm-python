from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any

from fairlead._skill import define_skill
from fairlead._types import OperationDef, Skill


@dataclass(frozen=True)
class FileChange:
    path: str
    status: str  # "added" | "modified" | "deleted" | "renamed" | "copied"
    old_path: str | None = None


@dataclass(frozen=True)
class GitStatus:
    branch: str
    ahead: int = 0
    behind: int = 0
    staged: list[FileChange] = field(default_factory=list)
    unstaged: list[FileChange] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    upstream: str | None = None


@dataclass(frozen=True)
class DiffFile:
    path: str
    additions: int
    deletions: int


@dataclass(frozen=True)
class Commit:
    hash: str
    short_hash: str
    author: str
    email: str
    date: str
    message: str


@dataclass(frozen=True)
class Branch:
    name: str
    current: bool


STATUS_MAP: dict[str, str] = {
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
}


def _parse_status_code(code: str) -> str:
    return STATUS_MAP.get(code, "modified")


def _parse_status(output: str) -> GitStatus:
    branch = ""
    upstream: str | None = None
    ahead = 0
    behind = 0
    staged: list[FileChange] = []
    unstaged: list[FileChange] = []
    untracked: list[str] = []

    for line in output.split("\n"):
        if not line:
            continue

        if line.startswith("# branch.head "):
            branch = line[len("# branch.head "):]
        elif line.startswith("# branch.upstream "):
            upstream = line[len("# branch.upstream "):]
        elif line.startswith("# branch.ab "):
            m = re.search(r"\+(\d+) -(\d+)", line)
            if m:
                ahead = int(m.group(1))
                behind = int(m.group(2))
        elif line.startswith("1 ") or line.startswith("2 "):
            parts = line.split(" ")
            xy = parts[1]
            staged_code = xy[0]
            unstaged_code = xy[1]

            if line.startswith("2 "):
                tab_index = line.index("\t")
                paths = line[tab_index + 1:].split("\t")
                old_path = paths[0]
                new_path = paths[1] if len(paths) > 1 else paths[0]

                if staged_code != ".":
                    staged.append(
                        FileChange(
                            path=new_path,
                            status=_parse_status_code(staged_code),
                            old_path=old_path,
                        )
                    )
                if unstaged_code != ".":
                    unstaged.append(
                        FileChange(
                            path=new_path,
                            status=_parse_status_code(unstaged_code),
                            old_path=old_path,
                        )
                    )
            else:
                path = " ".join(parts[8:])

                if staged_code != ".":
                    staged.append(FileChange(path=path, status=_parse_status_code(staged_code)))
                if unstaged_code != ".":
                    unstaged.append(FileChange(path=path, status=_parse_status_code(unstaged_code)))
        elif line.startswith("? "):
            untracked.append(line[2:])

    return GitStatus(
        branch=branch,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        staged=staged,
        unstaged=unstaged,
        untracked=untracked,
    )


def _parse_diff(output: str) -> list[DiffFile]:
    files: list[DiffFile] = []
    for line in output.split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            files.append(
                DiffFile(
                    additions=0 if parts[0] == "-" else int(parts[0]),
                    deletions=0 if parts[1] == "-" else int(parts[1]),
                    path=parts[2],
                )
            )
    return files


def _parse_log(output: str) -> list[Commit]:
    commits: list[Commit] = []
    for line in output.split("\n"):
        if not line:
            continue
        parts = line.split("\x00")
        if len(parts) >= 6:
            commits.append(
                Commit(
                    hash=parts[0],
                    short_hash=parts[1],
                    author=parts[2],
                    email=parts[3],
                    date=parts[4],
                    message=parts[5],
                )
            )
    return commits


async def _run_git(args: list[str], cwd: str | None = None) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        err_msg = stderr.decode().strip() if stderr else f"exit code {proc.returncode}"
        raise RuntimeError(f"git {args[0]} failed: {err_msg}")

    return stdout.decode() if stdout else ""


def git(*, cwd: str | None = None) -> Skill:
    async def status() -> GitStatus:
        output = await _run_git(["status", "--porcelain=v2", "--branch"], cwd)
        return _parse_status(output)

    async def diff(opts: dict[str, Any] | None = None) -> dict[str, list[DiffFile]]:
        args = ["diff", "--numstat"]
        if opts and opts.get("staged"):
            args.append("--cached")
        if opts and opts.get("ref"):
            args.append(str(opts["ref"]))
        output = await _run_git(args, cwd)
        return {"files": _parse_diff(output)}

    async def log(opts: dict[str, Any] | None = None) -> dict[str, list[Commit]]:
        limit = int(opts.get("limit", 10)) if opts else 10
        args = [
            "log",
            "--format=%H%x00%h%x00%an%x00%ae%x00%aI%x00%s",
            f"-n{limit}",
        ]
        if opts and opts.get("ref"):
            args.append(str(opts["ref"]))
        output = await _run_git(args, cwd)
        return {"commits": _parse_log(output)}

    async def show(
        ref: str, opts: dict[str, str] | None = None
    ) -> dict[str, str]:
        target = f"{ref}:{opts['path']}" if opts and opts.get("path") else ref
        content = await _run_git(["show", target], cwd)
        return {"content": content}

    async def add(paths: list[str]) -> None:
        await _run_git(["add", "--", *paths], cwd)

    async def commit(message: str) -> dict[str, str]:
        output = await _run_git(["commit", "-m", message], cwd)
        m = re.search(r"\[[\w/.-]+ ([a-f0-9]+)\]", output)
        hash_val = m.group(1) if m else ""
        return {"hash": hash_val}

    async def branch_list() -> dict[str, Any]:
        output = await _run_git(
            ["branch", "--list", "--format=%(HEAD)%(refname:short)"], cwd
        )
        branches: list[Branch] = []
        current = ""
        for line in output.split("\n"):
            if not line:
                continue
            is_current = line.startswith("*")
            name = line[1:]
            branches.append(Branch(name=name, current=is_current))
            if is_current:
                current = name
        return {"branches": branches, "current": current}

    async def branch_create(
        name: str, opts: dict[str, str] | None = None
    ) -> None:
        args = ["branch", name]
        if opts and opts.get("start_point"):
            args.append(opts["start_point"])
        await _run_git(args, cwd)

    async def checkout(ref: str) -> None:
        await _run_git(["checkout", ref], cwd)

    return define_skill(
        name="git",
        description="Git operations — status, diff, log, show, add, commit, branches, checkout",
        operations={
            "status": OperationDef(
                description="Get repository status with branch info and file changes",
                signature="() -> GitStatus",
                default_permission="allow",
                tags=["git", "status", "changes", "staged", "unstaged", "branch"],
                handler=status,
            ),
            "diff": OperationDef(
                description="Show file changes with additions/deletions counts",
                signature="(opts: dict | None = None) -> dict[str, list[DiffFile]]",
                default_permission="allow",
                tags=["git", "diff", "changes", "delta", "compare"],
                handler=diff,
            ),
            "log": OperationDef(
                description="Show commit history",
                signature="(opts: dict | None = None) -> dict[str, list[Commit]]",
                default_permission="allow",
                tags=["git", "log", "history", "commits", "recent"],
                handler=log,
            ),
            "show": OperationDef(
                description="Show content of a commit or file at a ref",
                signature="(ref: str, opts: dict | None = None) -> dict[str, str]",
                default_permission="allow",
                tags=["git", "show", "content", "ref", "commit", "file", "blob"],
                handler=show,
            ),
            "add": OperationDef(
                description="Stage files for commit",
                signature="(paths: list[str]) -> None",
                default_permission="ask",
                tags=["git", "add", "stage", "track"],
                handler=add,
            ),
            "commit": OperationDef(
                description="Create a commit with the given message",
                signature="(message: str) -> dict[str, str]",
                default_permission="ask",
                tags=["git", "commit", "save", "snapshot"],
                handler=commit,
            ),
            "branch_list": OperationDef(
                description="List branches",
                signature="() -> dict[str, Any]",
                default_permission="allow",
                tags=["git", "branch", "list", "branches"],
                handler=branch_list,
            ),
            "branch_create": OperationDef(
                description="Create a new branch",
                signature="(name: str, opts: dict | None = None) -> None",
                default_permission="ask",
                tags=["git", "branch", "create", "new"],
                handler=branch_create,
            ),
            "checkout": OperationDef(
                description="Switch branches or restore working tree files",
                signature="(ref: str) -> None",
                default_permission="ask",
                tags=["git", "checkout", "switch", "branch", "restore"],
                handler=checkout,
            ),
        },
    )
