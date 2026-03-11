from __future__ import annotations

import dataclasses
import json
import sys
from typing import Any

from fairlead._fairlead import Fairlead
from fairlead._permissions import PermissionDeniedError


def _serialize(obj: Any) -> Any:
    """Recursively serialize dataclasses, dicts, lists, and primitives to JSON-safe types."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    return str(obj)


async def _handle_message(agent: Fairlead, message: dict[str, Any]) -> dict[str, Any] | None:
    """Handle a single JSON-RPC 2.0 message. Returns a response dict, or None for notifications."""
    method = message.get("method", "")
    msg_id = message.get("id")
    params = message.get("params", {})

    # Notifications (no id) don't get responses
    if msg_id is None:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2025-11-25",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fairlead-mcp", "version": "0.1.0"},
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": [
                    {
                        "name": "search",
                        "description": "Search for operations by name, description, or tags",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query",
                                }
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "call",
                        "description": "Call an operation by qualified name (skill.operation) with keyword arguments",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Qualified operation name (e.g. 'git.status')",
                                },
                                "args": {
                                    "type": "object",
                                    "description": "Keyword arguments to pass to the operation",
                                },
                            },
                            "required": ["name"],
                        },
                    },
                    {
                        "name": "run",
                        "description": (
                            "Execute a Python code block with the agent in scope. "
                            "Use `await agent.call(name, args)` to invoke operations. "
                            "Use `agent.search(query)` to discover operations. "
                            "The last expression is returned automatically. "
                            "print() output is captured. "
                            "Chain multiple operations with loops, conditionals, and variables "
                            "to accomplish complex tasks in a single round-trip."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "code": {
                                    "type": "string",
                                    "description": "Python code to execute. `agent` is available for calling operations.",
                                }
                            },
                            "required": ["code"],
                        },
                    },
                ]
            },
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "search":
                query = arguments.get("query", "")
                results = agent.search(query)
                content = _serialize(results)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(content, indent=2)}
                        ]
                    },
                }
            elif tool_name == "call":
                op_name = arguments.get("name", "")
                args = arguments.get("args", {})
                result = await agent.call(op_name, args or None)
                content = _serialize(result)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(content, indent=2)}
                        ]
                    },
                }
            elif tool_name == "run":
                code = arguments.get("code", "")
                run_result = await agent.run(code)
                parts: list[dict[str, str]] = []
                if run_result.stdout:
                    parts.append({"type": "text", "text": run_result.stdout})
                result_content = _serialize(run_result.result)
                parts.append({"type": "text", "text": json.dumps(result_content, indent=2)})
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": parts},
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32602,
                        "message": f"Unknown tool: {tool_name}",
                    },
                }
        except PermissionDeniedError as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {"type": "text", "text": str(e)}
                    ],
                    "isError": True,
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {"type": "text", "text": f"Error: {e}"}
                    ],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


async def serve(agent: Fairlead) -> None:
    """Run the MCP server over stdio (one JSON-RPC message per line)."""
    for line_str in sys.stdin:
        line_str = line_str.strip()
        if not line_str:
            continue

        try:
            message = json.loads(line_str)
        except json.JSONDecodeError:
            error_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            sys.stdout.write(json.dumps(error_resp) + "\n")
            sys.stdout.flush()
            continue

        response = await _handle_message(agent, message)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
