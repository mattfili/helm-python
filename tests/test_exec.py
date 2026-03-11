"""Tests for Code Mode: agent.run() and the MCP 'run' tool."""

from __future__ import annotations

import pytest

from fairlead import Fairlead, FairleadOptions, OperationDef, define_skill


def _make_agent() -> Fairlead:
    math_skill = define_skill(
        name="math",
        description="Math operations",
        operations={
            "add": OperationDef(
                description="Add two numbers",
                handler=lambda a, b: a + b,
            ),
            "multiply": OperationDef(
                description="Multiply two numbers",
                handler=lambda a, b: a * b,
            ),
        },
    )
    return Fairlead(FairleadOptions(default_permission="allow")).use(math_skill)


class TestRun:
    @pytest.mark.asyncio
    async def test_last_expression_returned(self) -> None:
        agent = _make_agent()
        result = await agent.run("1 + 2")
        assert result.result == 3

    @pytest.mark.asyncio
    async def test_multi_line_last_expression(self) -> None:
        agent = _make_agent()
        result = await agent.run("x = 10\ny = 20\nx + y")
        assert result.result == 30

    @pytest.mark.asyncio
    async def test_no_return_value(self) -> None:
        agent = _make_agent()
        result = await agent.run("x = 42")
        assert result.result is None

    @pytest.mark.asyncio
    async def test_captures_stdout(self) -> None:
        agent = _make_agent()
        result = await agent.run('print("hello world")')
        assert "hello world" in result.stdout

    @pytest.mark.asyncio
    async def test_call_single_operation(self) -> None:
        agent = _make_agent()
        result = await agent.run(
            'await agent.call("math.add", {"a": 3, "b": 4})'
        )
        assert result.result == 7

    @pytest.mark.asyncio
    async def test_chain_multiple_operations(self) -> None:
        agent = _make_agent()
        code = """\
sum_result = await agent.call("math.add", {"a": 3, "b": 4})
await agent.call("math.multiply", {"a": sum_result, "b": 10})
"""
        result = await agent.run(code)
        assert result.result == 70

    @pytest.mark.asyncio
    async def test_loop_over_operations(self) -> None:
        agent = _make_agent()
        code = """\
total = 0
for i in range(5):
    total = await agent.call("math.add", {"a": total, "b": i})
total
"""
        result = await agent.run(code)
        assert result.result == 10  # 0+0+1+2+3+4

    @pytest.mark.asyncio
    async def test_conditional_logic(self) -> None:
        agent = _make_agent()
        code = """\
x = await agent.call("math.add", {"a": 1, "b": 1})
if x > 1:
    result = await agent.call("math.multiply", {"a": x, "b": 100})
else:
    result = 0
result
"""
        result = await agent.run(code)
        assert result.result == 200

    @pytest.mark.asyncio
    async def test_imports_work(self) -> None:
        agent = _make_agent()
        result = await agent.run("import json\njson.dumps({'a': 1})")
        assert result.result == '{"a": 1}'

    @pytest.mark.asyncio
    async def test_syntax_error_propagates(self) -> None:
        agent = _make_agent()
        with pytest.raises(SyntaxError):
            await agent.run("def def def")

    @pytest.mark.asyncio
    async def test_runtime_error_propagates(self) -> None:
        agent = _make_agent()
        with pytest.raises(ZeroDivisionError):
            await agent.run("1 / 0")

    @pytest.mark.asyncio
    async def test_permission_denied_propagates(self) -> None:
        from fairlead import PermissionDeniedError

        math_skill = define_skill(
            name="math",
            description="Math",
            operations={
                "add": OperationDef(
                    description="Add",
                    handler=lambda a, b: a + b,
                    default_permission="deny",
                ),
            },
        )
        agent = Fairlead(FairleadOptions(default_permission="deny")).use(math_skill)
        with pytest.raises(PermissionDeniedError):
            await agent.run('await agent.call("math.add", {"a": 1, "b": 2})')

    @pytest.mark.asyncio
    async def test_attribute_access_in_run(self) -> None:
        agent = _make_agent()
        result = await agent.run("await agent.math.add(a=5, b=6)")
        assert result.result == 11

    @pytest.mark.asyncio
    async def test_search_in_run(self) -> None:
        agent = _make_agent()
        result = await agent.run(
            "results = agent.search('add')\nlen(results)"
        )
        assert result.result >= 1
