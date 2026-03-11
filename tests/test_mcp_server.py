import json

import pytest

from fairlead import (
    FairleadOptions,
    OperationDef,
    PermissionDeniedError,
    create_fairlead,
    define_skill,
)
from fairlead._mcp_server import _handle_message, _serialize


def _make_agent():
    skill = define_skill(
        name="test",
        description="Test skill",
        operations={
            "add": OperationDef(
                description="Add numbers",
                signature="(a: int, b: int) -> int",
                default_permission="allow",
                tags=["math"],
                handler=lambda a, b: a + b,
            ),
            "greet": OperationDef(
                description="Greet someone",
                signature="(name: str) -> str",
                default_permission="allow",
                tags=["greeting"],
                handler=lambda name: f"hello {name}",
            ),
            "secret": OperationDef(
                description="Secret operation",
                default_permission="deny",
                handler=lambda: "secret",
            ),
        },
    )
    return create_fairlead(FairleadOptions(default_permission="allow")).use(skill)


class TestInitialize:
    @pytest.mark.asyncio
    async def test_returns_capabilities(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        })
        assert resp is not None
        assert resp["id"] == 1
        result = resp["result"]
        assert result["protocolVersion"] == "2025-11-25"
        assert "tools" in result["capabilities"]
        assert result["serverInfo"]["name"] == "fairlead-mcp"


class TestNotifications:
    @pytest.mark.asyncio
    async def test_notification_returns_none(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })
        assert resp is None


class TestPing:
    @pytest.mark.asyncio
    async def test_ping(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "ping",
        })
        assert resp is not None
        assert resp["id"] == 2
        assert resp["result"] == {}


class TestToolsList:
    @pytest.mark.asyncio
    async def test_returns_three_tools(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/list",
        })
        assert resp is not None
        tools = resp["result"]["tools"]
        assert len(tools) == 3
        names = {t["name"] for t in tools}
        assert names == {"search", "call", "run"}

    @pytest.mark.asyncio
    async def test_search_tool_has_schema(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/list",
        })
        tools = resp["result"]["tools"]
        search_tool = next(t for t in tools if t["name"] == "search")
        assert "query" in search_tool["inputSchema"]["properties"]

    @pytest.mark.asyncio
    async def test_call_tool_has_schema(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/list",
        })
        tools = resp["result"]["tools"]
        call_tool = next(t for t in tools if t["name"] == "call")
        assert "name" in call_tool["inputSchema"]["properties"]
        assert "args" in call_tool["inputSchema"]["properties"]


class TestSearchDispatch:
    @pytest.mark.asyncio
    async def test_search_returns_results(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": "add"},
            },
        })
        assert resp is not None
        content = resp["result"]["content"]
        assert len(content) == 1
        data = json.loads(content[0]["text"])
        assert isinstance(data, list)
        assert any(r["qualified_name"] == "test.add" for r in data)

    @pytest.mark.asyncio
    async def test_search_empty_query(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {"query": "nonexistent_xyz_123"},
            },
        })
        assert resp is not None
        data = json.loads(resp["result"]["content"][0]["text"])
        assert data == []


class TestCallDispatch:
    @pytest.mark.asyncio
    async def test_call_operation(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "call",
                "arguments": {"name": "test.add", "args": {"a": 2, "b": 3}},
            },
        })
        assert resp is not None
        data = json.loads(resp["result"]["content"][0]["text"])
        assert data == 5

    @pytest.mark.asyncio
    async def test_call_with_string_result(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "call",
                "arguments": {"name": "test.greet", "args": {"name": "world"}},
            },
        })
        assert resp is not None
        data = json.loads(resp["result"]["content"][0]["text"])
        assert data == "hello world"


class TestRunDispatch:
    @pytest.mark.asyncio
    async def test_run_simple_expression(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/call",
            "params": {
                "name": "run",
                "arguments": {"code": "1 + 2"},
            },
        })
        assert resp is not None
        content = resp["result"]["content"]
        data = json.loads(content[-1]["text"])
        assert data == 3

    @pytest.mark.asyncio
    async def test_run_chains_operations(self) -> None:
        agent = _make_agent()
        code = (
            'x = await agent.call("test.add", {"a": 3, "b": 4})\n'
            'await agent.call("test.greet", {"name": str(x)})'
        )
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 21,
            "method": "tools/call",
            "params": {
                "name": "run",
                "arguments": {"code": code},
            },
        })
        assert resp is not None
        content = resp["result"]["content"]
        data = json.loads(content[-1]["text"])
        assert data == "hello 7"

    @pytest.mark.asyncio
    async def test_run_captures_stdout(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 22,
            "method": "tools/call",
            "params": {
                "name": "run",
                "arguments": {"code": 'print("from run")\n42'},
            },
        })
        assert resp is not None
        content = resp["result"]["content"]
        assert len(content) == 2  # stdout + result
        assert "from run" in content[0]["text"]

    @pytest.mark.asyncio
    async def test_run_error_is_reported(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 23,
            "method": "tools/call",
            "params": {
                "name": "run",
                "arguments": {"code": "1 / 0"},
            },
        })
        assert resp is not None
        assert resp["result"]["isError"] is True


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_permission_denied(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "call",
                "arguments": {"name": "test.secret"},
            },
        })
        assert resp is not None
        assert resp["result"]["isError"] is True
        assert "Permission denied" in resp["result"]["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_unknown_tool(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "unknown_tool",
                "arguments": {},
            },
        })
        assert resp is not None
        assert "error" in resp
        assert resp["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_unknown_method(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "unknown/method",
        })
        assert resp is not None
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_invalid_operation_name(self) -> None:
        agent = _make_agent()
        resp = await _handle_message(agent, {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {
                "name": "call",
                "arguments": {"name": "invalid"},
            },
        })
        assert resp is not None
        assert resp["result"]["isError"] is True


class TestSerialize:
    def test_primitives(self) -> None:
        assert _serialize(42) == 42
        assert _serialize("hello") == "hello"
        assert _serialize(True) is True
        assert _serialize(None) is None

    def test_dict(self) -> None:
        assert _serialize({"a": 1}) == {"a": 1}

    def test_list(self) -> None:
        assert _serialize([1, 2, 3]) == [1, 2, 3]

    def test_nested(self) -> None:
        assert _serialize({"a": [1, {"b": 2}]}) == {"a": [1, {"b": 2}]}
