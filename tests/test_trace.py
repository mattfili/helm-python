"""Tests for execution tracing in Code Mode."""

from __future__ import annotations

import pytest

from fairlead import (
    Fairlead,
    FairleadOptions,
    OperationDef,
    PermissionDeniedError,
    TraceEntry,
    define_skill,
)


def _make_agent(default_permission: str = "allow") -> Fairlead:
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
    return Fairlead(FairleadOptions(default_permission=default_permission)).use(
        math_skill
    )


def _make_agent_with_deny() -> Fairlead:
    skill = define_skill(
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
    return Fairlead(FairleadOptions(default_permission="allow")).use(skill)


def _make_agent_with_error() -> Fairlead:
    def _fail(**kwargs):
        raise ValueError("boom")

    skill = define_skill(
        name="math",
        description="Math",
        operations={
            "explode": OperationDef(
                description="Always fails",
                handler=_fail,
            ),
        },
    )
    return Fairlead(FairleadOptions(default_permission="allow")).use(skill)


class TestSingleCall:
    @pytest.mark.asyncio
    async def test_single_call_produces_trace(self) -> None:
        agent = _make_agent()
        result = await agent.run(
            'await agent.call("math.add", {"a": 1, "b": 2})'
        )
        assert len(result.trace) == 1

    @pytest.mark.asyncio
    async def test_trace_entry_fields_correct(self) -> None:
        agent = _make_agent()
        result = await agent.run(
            'await agent.call("math.add", {"a": 1, "b": 2})'
        )
        entry = result.trace[0]
        assert entry.operation == "math.add"
        assert entry.args == {"a": 1, "b": 2}
        assert entry.result == 3
        assert entry.error is None
        assert entry.permission == "allow"
        assert entry.duration_ms > 0


class TestMultipleCalls:
    @pytest.mark.asyncio
    async def test_multiple_calls_ordered(self) -> None:
        agent = _make_agent()
        code = """\
await agent.call("math.add", {"a": 1, "b": 2})
await agent.call("math.multiply", {"a": 3, "b": 4})
await agent.call("math.add", {"a": 10, "b": 20})
"""
        result = await agent.run(code)
        assert len(result.trace) == 3
        assert result.trace[0].operation == "math.add"
        assert result.trace[0].result == 3
        assert result.trace[1].operation == "math.multiply"
        assert result.trace[1].result == 12
        assert result.trace[2].operation == "math.add"
        assert result.trace[2].result == 30

    @pytest.mark.asyncio
    async def test_loop_calls_traced(self) -> None:
        agent = _make_agent()
        code = """\
total = 0
for i in range(5):
    total = await agent.call("math.add", {"a": total, "b": i})
total
"""
        result = await agent.run(code)
        assert result.result == 10
        assert len(result.trace) == 5

    @pytest.mark.asyncio
    async def test_conditional_branch_traced(self) -> None:
        agent = _make_agent()
        code = """\
x = await agent.call("math.add", {"a": 1, "b": 1})
if x > 1:
    result = await agent.call("math.multiply", {"a": x, "b": 100})
else:
    result = await agent.call("math.add", {"a": x, "b": 0})
result
"""
        result = await agent.run(code)
        assert result.result == 200
        assert len(result.trace) == 2
        assert result.trace[1].operation == "math.multiply"


class TestPermissionDenied:
    @pytest.mark.asyncio
    async def test_permission_denied_traced(self) -> None:
        agent = _make_agent_with_deny()
        code = """\
try:
    await agent.call("math.add", {"a": 1, "b": 2})
except Exception:
    pass
"done"
"""
        result = await agent.run(code)
        assert result.result == "done"
        assert len(result.trace) == 1
        entry = result.trace[0]
        assert entry.operation == "math.add"
        assert entry.error == "PermissionDeniedError"
        assert entry.permission == "deny"


class TestNoTraceOutsideRun:
    @pytest.mark.asyncio
    async def test_no_trace_outside_run(self) -> None:
        from fairlead._trace import get_trace

        agent = _make_agent()
        await agent.call("math.add", {"a": 1, "b": 2})
        assert get_trace() is None


class TestAttributeAccess:
    @pytest.mark.asyncio
    async def test_attribute_access_traced(self) -> None:
        agent = _make_agent()
        result = await agent.run("await agent.math.add(a=1, b=2)")
        assert len(result.trace) == 1
        assert result.trace[0].operation == "math.add"
        assert result.trace[0].result == 3


class TestHandlerError:
    @pytest.mark.asyncio
    async def test_handler_error_traced(self) -> None:
        agent = _make_agent_with_error()
        code = """\
try:
    await agent.call("math.explode", {})
except ValueError:
    pass
"caught"
"""
        result = await agent.run(code)
        assert result.result == "caught"
        assert len(result.trace) == 1
        entry = result.trace[0]
        assert entry.operation == "math.explode"
        assert "boom" in entry.error
        assert entry.duration_ms >= 0


class TestPurePython:
    @pytest.mark.asyncio
    async def test_empty_trace_for_pure_python(self) -> None:
        agent = _make_agent()
        result = await agent.run("1 + 2")
        assert result.result == 3
        assert result.trace == []


class TestNestedRun:
    @pytest.mark.asyncio
    async def test_nested_run_separate_traces(self) -> None:
        agent = _make_agent()
        code = """\
await agent.call("math.add", {"a": 1, "b": 2})
inner = await agent.run('await agent.call("math.multiply", {"a": 3, "b": 4})')
await agent.call("math.add", {"a": 5, "b": 6})
inner
"""
        result = await agent.run(code)
        # Outer trace: 2 add calls (inner run's ops are in the inner trace)
        assert len(result.trace) == 2
        assert result.trace[0].operation == "math.add"
        assert result.trace[0].result == 3
        assert result.trace[1].operation == "math.add"
        assert result.trace[1].result == 11
        # Inner result has its own trace
        inner_result = result.result
        assert len(inner_result.trace) == 1
        assert inner_result.trace[0].operation == "math.multiply"
        assert inner_result.trace[0].result == 12
