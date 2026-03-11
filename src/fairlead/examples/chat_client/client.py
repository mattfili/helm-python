"""MCP client — manages a fairlead MCP server subprocess and JSON-RPC communication."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any


class MCPClient:
    """Spawns a fairlead MCP server and communicates via JSON-RPC over stdio."""

    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._tools: list[dict[str, Any]] = []

    async def start(self) -> None:
        """Start the MCP server subprocess and initialize the connection."""
        self._process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "fairlead.examples.mcp_server",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Initialize the MCP connection
        await self._send("initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "fairlead-chat", "version": "0.1.0"},
        })

        # Send initialized notification (no id = notification, no response expected)
        self._write({"jsonrpc": "2.0", "method": "notifications/initialized"})

        # Discover available tools
        result = await self._send("tools/list", {})
        self._tools = result.get("tools", [])

    async def stop(self) -> None:
        """Terminate the server subprocess."""
        if self._process and self._process.returncode is None:
            self._process.terminate()
            await self._process.wait()

    @property
    def tools(self) -> list[dict[str, Any]]:
        """Tool definitions suitable for the Anthropic API."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["inputSchema"],
            }
            for t in self._tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Call an MCP tool and return the text result."""
        result = await self._send("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        contents = result.get("content", [])
        return "\n".join(c.get("text", "") for c in contents)

    def _write(self, message: dict[str, Any]) -> None:
        assert self._process and self._process.stdin
        data = json.dumps(message) + "\n"
        self._process.stdin.write(data.encode())

    async def _send(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request and wait for the response."""
        assert self._process and self._process.stdin and self._process.stdout

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        self._write(request)
        await self._process.stdin.drain()

        line = await self._process.stdout.readline()
        response = json.loads(line.decode())

        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")

        return response.get("result", {})
