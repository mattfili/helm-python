# 05 — Chat Client

A terminal chat application that spawns helm's MCP server as a subprocess and communicates via JSON-RPC over stdio. Integrates with the Anthropic API for the LLM loop.

## What You'll Learn

- Spawning an MCP server as a subprocess
- Sending/receiving JSON-RPC messages over stdio
- Integrating helm tools with the Anthropic API
- Building a complete agent loop (user -> LLM -> tool -> LLM -> user)

## Prerequisites

```bash
pip install -e ../..
pip install -r requirements.txt   # installs anthropic SDK
export ANTHROPIC_API_KEY="your-key-here"
```

## Run It

```bash
python chat.py
```

Type messages at the prompt. The LLM can search for and call helm operations. Type `quit` to exit.

## Architecture

```
User <-> chat.py <-> Anthropic API
                        |
                        v (tool calls)
              client.py (JSON-RPC)
                        |
                        v (stdio)
              server.py (helm MCP server)
```

`client.py` manages the subprocess and JSON-RPC protocol. `chat.py` runs the LLM loop, routing tool calls through the client.
