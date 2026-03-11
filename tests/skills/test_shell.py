import pytest

from fairlead import FairleadOptions, create_fairlead
from fairlead.skills import shell
from fairlead.skills._shell import ShellExecOptions


def agent():
    return create_fairlead(FairleadOptions(permissions={"shell.*": "allow"})).use(shell())


class TestShellSkill:
    @pytest.mark.asyncio
    async def test_simple_command(self) -> None:
        result = await agent().shell.dangerous_exec("echo hello")
        assert result.stdout.strip() == "hello"
        assert result.stderr == ""
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_captures_stderr(self) -> None:
        result = await agent().shell.dangerous_exec("echo err >&2")
        assert result.stderr.strip() == "err"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_nonzero_exit_code(self) -> None:
        result = await agent().shell.dangerous_exec("exit 42")
        assert result.exit_code == 42

    @pytest.mark.asyncio
    async def test_stdin(self) -> None:
        result = await agent().shell.dangerous_exec(
            "cat", ShellExecOptions(stdin="from stdin")
        )
        assert result.stdout == "from stdin"

    @pytest.mark.asyncio
    async def test_pipes(self) -> None:
        result = await agent().shell.dangerous_exec(
            "echo 'a b c' | tr ' ' '\\n' | wc -l"
        )
        assert result.stdout.strip() == "3"

    @pytest.mark.asyncio
    async def test_factory_cwd(self) -> None:
        a = create_fairlead(FairleadOptions(permissions={"shell.*": "allow"})).use(
            shell(cwd="/tmp")
        )
        result = await a.shell.dangerous_exec("pwd")
        # On macOS /tmp -> /private/tmp
        assert result.stdout.strip().endswith("/tmp")

    @pytest.mark.asyncio
    async def test_per_call_cwd_override(self) -> None:
        a = create_fairlead(FairleadOptions(permissions={"shell.*": "allow"})).use(
            shell(cwd="/tmp")
        )
        result = await a.shell.dangerous_exec(
            "pwd", ShellExecOptions(cwd="/")
        )
        assert result.stdout.strip() == "/"

    @pytest.mark.asyncio
    async def test_factory_env(self) -> None:
        a = create_fairlead(FairleadOptions(permissions={"shell.*": "allow"})).use(
            shell(env={"HELM_TEST_VAR": "from_factory"})
        )
        result = await a.shell.dangerous_exec("echo $HELM_TEST_VAR")
        assert result.stdout.strip() == "from_factory"

    @pytest.mark.asyncio
    async def test_merge_env(self) -> None:
        a = create_fairlead(FairleadOptions(permissions={"shell.*": "allow"})).use(
            shell(env={"HELM_A": "a"})
        )
        result = await a.shell.dangerous_exec(
            "echo $HELM_A $HELM_B", ShellExecOptions(env={"HELM_B": "b"})
        )
        assert result.stdout.strip() == "a b"
