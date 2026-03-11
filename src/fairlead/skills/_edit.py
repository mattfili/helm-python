from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

from fairlead._skill import define_skill
from fairlead._types import OperationDef, Skill


@dataclass(frozen=True)
class InsertOp:
    type: str  # "insert"
    line: int
    content: str


@dataclass(frozen=True)
class RemoveOp:
    type: str  # "remove"
    start: int
    end: int


@dataclass(frozen=True)
class ReplaceOp:
    type: str  # "replace"
    start: int
    end: int
    content: str


EditOp = Union[InsertOp, RemoveOp, ReplaceOp, dict[str, Any]]


def edit() -> Skill:
    async def replace(
        path: str,
        old: str,
        new_: str,
        opts: dict[str, bool] | None = None,
    ) -> dict[str, int]:
        def _replace() -> dict[str, int]:
            content = Path(path).read_text(encoding="utf-8")
            count = 0

            if opts and opts.get("all"):
                result = content
                while old in result:
                    result = result.replace(old, new_, 1)
                    count += 1
            else:
                if old in content:
                    result = content.replace(old, new_, 1)
                    count = 1
                else:
                    result = content

            if count > 0:
                Path(path).write_text(result, encoding="utf-8")
            return {"count": count}

        return await asyncio.to_thread(_replace)

    async def insert(path: str, line: int, content: str) -> None:
        def _insert() -> None:
            file_content = Path(path).read_text(encoding="utf-8")
            lines = file_content.split("\n")
            index = max(0, min(line - 1, len(lines)))
            lines.insert(index, content)
            Path(path).write_text("\n".join(lines), encoding="utf-8")

        await asyncio.to_thread(_insert)

    async def remove_lines(path: str, start: int, end: int) -> None:
        def _remove() -> None:
            file_content = Path(path).read_text(encoding="utf-8")
            lines = file_content.split("\n")
            s = max(0, start - 1)
            e = min(len(lines), end)
            del lines[s:e]
            Path(path).write_text("\n".join(lines), encoding="utf-8")

        await asyncio.to_thread(_remove)

    async def apply(path: str, edits: list[dict[str, Any]]) -> None:
        def _apply() -> None:
            file_content = Path(path).read_text(encoding="utf-8")
            lines = file_content.split("\n")

            def sort_key(op: dict[str, Any]) -> int:
                if op["type"] == "insert":
                    return int(op["line"])
                return int(op["start"])

            sorted_edits = sorted(edits, key=sort_key, reverse=True)

            for op in sorted_edits:
                if op["type"] == "insert":
                    index = max(0, min(int(op["line"]) - 1, len(lines)))
                    lines.insert(index, str(op["content"]))
                elif op["type"] == "remove":
                    s = max(0, int(op["start"]) - 1)
                    e = min(len(lines), int(op["end"]))
                    del lines[s:e]
                elif op["type"] == "replace":
                    s = max(0, int(op["start"]) - 1)
                    e = min(len(lines), int(op["end"]))
                    lines[s:e] = [str(op["content"])]

            Path(path).write_text("\n".join(lines), encoding="utf-8")

        await asyncio.to_thread(_apply)

    return define_skill(
        name="edit",
        description="File editing operations — replace text, insert lines, remove lines, apply batch edits",
        operations={
            "replace": OperationDef(
                description="Replace occurrences of a string in a file",
                signature="(path: str, old: str, new_: str, opts: dict | None = None) -> dict[str, int]",
                default_permission="ask",
                tags=["edit", "replace", "substitute", "find", "change", "sed"],
                handler=replace,
            ),
            "insert": OperationDef(
                description="Insert text at a line number (1-indexed)",
                signature="(path: str, line: int, content: str) -> None",
                default_permission="ask",
                tags=["edit", "insert", "add", "line", "append"],
                handler=insert,
            ),
            "remove_lines": OperationDef(
                description="Remove lines from start to end inclusive (1-indexed)",
                signature="(path: str, start: int, end: int) -> None",
                default_permission="ask",
                tags=["edit", "remove", "delete", "lines", "cut"],
                handler=remove_lines,
            ),
            "apply": OperationDef(
                description="Apply multiple edits atomically (sorted by line, applied bottom-up to preserve line numbers)",
                signature="(path: str, edits: list[dict]) -> None",
                default_permission="ask",
                tags=["edit", "batch", "multi", "atomic", "apply", "patch"],
                handler=apply,
            ),
        },
    )
