from __future__ import annotations

import ast
import contextlib
import io
import textwrap
from dataclasses import dataclass
from typing import Any


@dataclass
class RunResult:
    """Result of executing a code block."""

    result: Any
    stdout: str


def _wrap_async(code: str) -> str:
    """Wrap code in an async function. Auto-return the last expression."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Let it fail at runtime with a clear error
        return f"async def __fairlead_exec__():\n{textwrap.indent(code, '    ')}"

    if tree.body and isinstance(tree.body[-1], ast.Expr):
        return_node = ast.Return(value=tree.body[-1].value)
        ast.copy_location(return_node, tree.body[-1])
        tree.body[-1] = return_node
        code = ast.unparse(tree)

    return f"async def __fairlead_exec__():\n{textwrap.indent(code, '    ')}"


async def exec_code(agent: Any, code: str) -> RunResult:
    """Execute Python code with the fairlead agent available as ``agent``.

    The code runs inside an async function so ``await`` works directly.
    If the last statement is an expression, its value is returned automatically.
    ``print()`` output is captured in ``stdout``.
    """
    wrapped = _wrap_async(code)
    namespace: dict[str, Any] = {"agent": agent}

    exec(compile(wrapped, "<fairlead-exec>", "exec"), namespace)

    stdout_buf = io.StringIO()
    with contextlib.redirect_stdout(stdout_buf):
        return_value = await namespace["__fairlead_exec__"]()

    return RunResult(result=return_value, stdout=stdout_buf.getvalue())
