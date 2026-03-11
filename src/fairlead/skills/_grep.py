from __future__ import annotations

import asyncio
import fnmatch
import os
import re
from dataclasses import dataclass
from pathlib import Path

from fairlead._skill import define_skill
from fairlead._types import OperationDef, Skill


@dataclass(frozen=True)
class GrepContext:
    before: list[str]
    after: list[str]


@dataclass(frozen=True)
class GrepMatch:
    file: str
    line: int
    column: int
    text: str
    context: GrepContext | None = None


@dataclass(frozen=True)
class GrepOptions:
    path: str | None = None
    glob: str | None = None
    max_results: int | None = None
    context_lines: int | None = None
    ignore_case: bool = False


DEFAULT_SKIP = {"node_modules", ".git"}


def _parse_gitignore(content: str) -> list[str]:
    return [
        line.strip()
        for line in content.split("\n")
        if line.strip() and not line.strip().startswith("#")
    ]


def _is_ignored(relative_path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        clean = pattern.rstrip("/")
        parts = relative_path.replace("\\", "/").split("/")
        for part in parts:
            if fnmatch.fnmatch(part, clean):
                return True
    return False


def _is_binary(file_path: str) -> bool:
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(512)
        return b"\x00" in chunk
    except OSError:
        return True


def _collect_files(
    directory: str,
    base_dir: str,
    gitignore_patterns: list[str],
    glob_pattern: str | None,
) -> list[str]:
    files: list[str] = []
    try:
        entries = os.scandir(directory)
    except OSError:
        return files

    for entry in entries:
        if entry.name in DEFAULT_SKIP:
            continue

        relative = os.path.relpath(entry.path, base_dir)

        if _is_ignored(relative, gitignore_patterns):
            continue

        if entry.is_dir(follow_symlinks=False):
            files.extend(
                _collect_files(entry.path, base_dir, gitignore_patterns, glob_pattern)
            )
        elif entry.is_file(follow_symlinks=False):
            if glob_pattern and not fnmatch.fnmatch(entry.name, glob_pattern):
                continue
            files.append(entry.path)

    return files


def grep(*, cwd: str | None = None) -> Skill:
    async def search(
        pattern: str, opts: GrepOptions | None = None
    ) -> dict[str, list[GrepMatch]]:
        def _search() -> dict[str, list[GrepMatch]]:
            search_dir = (opts.path if opts else None) or cwd or os.getcwd()
            max_results = (opts.max_results if opts else None) or 100
            context_lines = (opts.context_lines if opts else None) or 0
            flags = re.IGNORECASE if (opts and opts.ignore_case) else 0
            regex = re.compile(pattern, flags)

            gitignore_patterns: list[str] = []
            gitignore_path = os.path.join(search_dir, ".gitignore")
            try:
                gitignore_patterns = _parse_gitignore(
                    Path(gitignore_path).read_text(encoding="utf-8")
                )
            except OSError:
                pass

            file_glob = opts.glob if opts else None
            all_files = _collect_files(search_dir, search_dir, gitignore_patterns, file_glob)
            matches: list[GrepMatch] = []

            for file_path in all_files:
                if len(matches) >= max_results:
                    break

                if _is_binary(file_path):
                    continue

                try:
                    content = Path(file_path).read_text(encoding="utf-8")
                except OSError:
                    continue

                lines = content.split("\n")
                for i, line_text in enumerate(lines):
                    if len(matches) >= max_results:
                        break

                    m = regex.search(line_text)
                    if m:
                        ctx: GrepContext | None = None
                        if context_lines > 0:
                            before_start = max(0, i - context_lines)
                            after_end = min(len(lines) - 1, i + context_lines)
                            ctx = GrepContext(
                                before=lines[before_start:i],
                                after=lines[i + 1 : after_end + 1],
                            )

                        matches.append(
                            GrepMatch(
                                file=file_path,
                                line=i + 1,
                                column=m.start() + 1,
                                text=line_text,
                                context=ctx,
                            )
                        )

            return {"matches": matches}

        return await asyncio.to_thread(_search)

    return define_skill(
        name="grep",
        description="Recursive file content search with regex pattern matching",
        operations={
            "search": OperationDef(
                description="Search files recursively for a regex pattern",
                signature="(pattern: str, opts: GrepOptions | None = None) -> dict[str, list[GrepMatch]]",
                default_permission="allow",
                tags=["search", "grep", "find", "regex", "pattern", "content", "text", "rg"],
                handler=search,
            ),
        },
    )
