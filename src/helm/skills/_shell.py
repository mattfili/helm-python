from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from helm._skill import define_skill
from helm._types import OperationDef, Skill


@dataclass(frozen=True)
class ShellExecOptions:
    cwd: str | None = None
    env: dict[str, str] | None = None
    timeout: float | None = None
    stdin: str | None = None


@dataclass(frozen=True)
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int


def shell(
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> Skill:
    async def dangerous_exec(
        command: str, opts: ShellExecOptions | None = None
    ) -> ExecResult:
        effective_cwd = (opts.cwd if opts else None) or cwd
        effective_timeout = (opts.timeout if opts else None) or timeout

        # Merge env: os.environ + factory env + per-call env
        effective_env: dict[str, str] | None = None
        if env or (opts and opts.env):
            effective_env = dict(os.environ)
            if env:
                effective_env.update(env)
            if opts and opts.env:
                effective_env.update(opts.env)

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if (opts and opts.stdin is not None) else None,
            cwd=effective_cwd,
            env=effective_env,
        )

        stdin_bytes = (opts.stdin.encode() if opts and opts.stdin is not None else None)

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=stdin_bytes),
                timeout=effective_timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ExecResult(stdout="", stderr="", exit_code=-1)

        return ExecResult(
            stdout=stdout_bytes.decode() if stdout_bytes else "",
            stderr=stderr_bytes.decode() if stderr_bytes else "",
            exit_code=proc.returncode or 0,
        )

    return define_skill(
        name="shell",
        description="Run shell commands and return structured output",
        operations={
            "dangerous_exec": OperationDef(
                description="Run a shell command",
                signature="(command: str, opts: ShellExecOptions | None = None) -> ExecResult",
                default_permission="ask",
                tags=["shell", "exec", "run", "command", "bash", "process"],
                handler=dangerous_exec,
            ),
        },
    )
