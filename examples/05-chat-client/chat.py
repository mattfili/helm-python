"""Terminal chat app — LLM + helm MCP tools via Anthropic API."""

from __future__ import annotations

import asyncio
import os

import anthropic

from client import MCPClient


async def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY environment variable first.")
        return

    # Start the MCP server and discover tools
    mcp = MCPClient()
    await mcp.start()
    print(f"Connected to helm MCP server ({len(mcp.tools)} tools available)")
    print("Type a message (or 'quit' to exit)\n")

    client = anthropic.Anthropic(api_key=api_key)
    messages: list[dict] = []

    try:
        while True:
            user_input = input("you> ").strip()
            if not user_input:
                continue
            if user_input.lower() == "quit":
                break

            messages.append({"role": "user", "content": user_input})

            # LLM loop — keep going until the model stops calling tools
            while True:
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system="You have access to helm tools. Use 'search' to find operations, then 'call' to invoke them. Be concise.",
                    tools=mcp.tools,
                    messages=messages,
                )

                # Collect assistant content blocks
                assistant_content = response.content
                messages.append({"role": "assistant", "content": assistant_content})

                # Check if the model wants to use tools
                tool_uses = [b for b in assistant_content if b.type == "tool_use"]
                if not tool_uses:
                    # No tool calls — print text and break
                    for block in assistant_content:
                        if block.type == "text" and block.text:
                            print(f"assistant> {block.text}")
                    break

                # Execute each tool call through MCP
                tool_results = []
                for tool_use in tool_uses:
                    try:
                        result = await mcp.call_tool(tool_use.name, tool_use.input)
                    except Exception as e:
                        result = f"Error: {e}"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result,
                    })

                messages.append({"role": "user", "content": tool_results})

    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
    finally:
        await mcp.stop()


if __name__ == "__main__":
    asyncio.run(main())
