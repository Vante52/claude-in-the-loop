"""
MCP client for the support agent.

This module replaces tool_runner.py from Stage 1. It:
  1. Starts mcp_server.py as a subprocess and talks MCP over stdio
  2. Discovers tools via list_tools() (so tools.py is no longer needed)
  3. Applies session-level gates before/after calling the server
"""

import json
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Any

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

# Path to mcp_server.py — same directory as this file
SERVER_SCRIPT = Path(__file__).resolve().parent / "mcp_server.py"


def mcp_tools_to_anthropic(tools_result) -> list[dict[str, Any]]:
    """
    Convert MCP tool definitions to the format Anthropic's messages.create() expects.

    MCP uses 'inputSchema'; Anthropic expects 'input_schema'. Same data, different key.
    """
    return [
        {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema,
        }
        for tool in tools_result.tools
    ]


def extract_tool_result_text(result: CallToolResult) -> str:
    """Pull plain text out of an MCP CallToolResult (FastMCP returns JSON strings as text)."""
    parts = [block.text for block in result.content if block.type == "text"]
    if parts:
        return "".join(parts)

    if result.isError:
        return json.dumps({
            "error": {
                "type": "validation",
                "retryable": False,
                "message": "Tool call failed on the MCP server.",
            }
        })

    return json.dumps({"error": {"type": "validation", "retryable": False, "message": "Empty tool result."}})


def check_refund_session_gates(
    customer_id: str,
    session_state: dict[str, Any],
) -> str | None:
    """
    Session-level gates for process_refund — run BEFORE calling the MCP server.

    Returns a JSON error string if blocked, or None if the call may proceed.
    These checks require conversation state that the MCP server does not have.
    """
    if not session_state.get("verified_customer_id"):
        return json.dumps({
            "error": {
                "type": "permission",
                "retryable": False,
                "message": (
                    "Cannot process a refund before customer identity has been "
                    "verified. Call get_customer first and confirm the customer's "
                    "identity before attempting a refund."
                ),
            }
        })

    if customer_id != session_state["verified_customer_id"]:
        return json.dumps({
            "error": {
                "type": "permission",
                "retryable": False,
                "message": (
                    f"Customer ID mismatch. The verified customer in this session is "
                    f"{session_state['verified_customer_id']} but the refund request "
                    f"is for {customer_id}. Do not process this refund. Verify you "
                    f"have the correct customer before continuing."
                ),
            }
        })

    return None


def update_session_after_get_customer(result_text: str, session_state: dict[str, Any]) -> None:
    """
    After a successful get_customer call, record verified identity in session_state.

    This replaces the side effect that lived inside tool_runner.get_customer in Stage 1.
    """
    try:
        payload = json.loads(result_text)
    except json.JSONDecodeError:
        return

    if "error" in payload:
        return

    customer_id = payload.get("customer_id")
    name = payload.get("name")
    if customer_id:
        session_state["verified_customer_id"] = customer_id
    if name:
        session_state["verified_customer_name"] = name

# MCP client session scoped to one agent conversation.
class MCPAgentTools:
    # Keeps one server subprocess alive for the whole conversation (efficient).
    def __init__(self) -> None:
        self._session: ClientSession | None = None
        self._anthropic_tools: list[dict[str, Any]] | None = None
        self._exit_stack: AsyncExitStack | None = None

    async def __aenter__(self) -> "MCPAgentTools":
        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()

		# 
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(SERVER_SCRIPT)],
            cwd=str(SERVER_SCRIPT.parent),
        )

        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        await self._session.initialize()

        tools_result = await self._session.list_tools()
        self._anthropic_tools = mcp_tools_to_anthropic(tools_result)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._exit_stack is not None:
            await self._exit_stack.__aexit__(exc_type, exc, tb)
        self._session = None
        self._anthropic_tools = None
        self._exit_stack = None

    @property
    def anthropic_tools(self) -> list[dict[str, Any]]:
        if self._anthropic_tools is None:
            raise RuntimeError("MCP session is not connected. Use 'async with MCPAgentTools()'.")
        return self._anthropic_tools

    # Execute a tool: apply session gates, call MCP, update session_state if needed.
    async def run_tool(self, tool_name: str, tool_input: dict[str, Any], session_state: dict[str, Any],) -> str:
        if self._session is None:
            raise RuntimeError("MCP session is not connected.")

        tool_input = tool_input or {}

        known_tool_names = {tool["name"] for tool in self.anthropic_tools}

        if tool_name not in known_tool_names:
            return json.dumps({
                "error": {
                    "type": "validation",
                    "retryable": False,
                    "message": f"Tool '{tool_name}' is not recognized.",
                }
            })

        # Gate 1: customer must be verified before any non-verification tool.
        if tool_name != "get_customer" and not session_state.get("verified_customer_id"):
            return json.dumps({
                "error": {
                    "type": "permission",
                    "retryable": False,
                    "message": (
                        f"Cannot use {tool_name} before customer identity has been "
                        "verified. Call get_customer first using the customer's name, "
                        "email address, or customer ID."
                    ),
                }
            })

        # Gate 2: refunds must match the verified customer.
        if tool_name == "process_refund":
            verified_customer_id = session_state.get("verified_customer_id")
            requested_customer_id = tool_input.get("customer_id")

            # Claude may omit customer_id even if the schema asks for it.
            # Since the host already knows the verified customer, inject it safely.
            if not requested_customer_id:
                tool_input["customer_id"] = verified_customer_id

            elif requested_customer_id != verified_customer_id:
                return json.dumps({
                    "error": {
                        "type": "permission",
                        "retryable": False,
                        "message": (
                            f"Customer ID mismatch. The verified customer in this session is "
                            f"{verified_customer_id}, but the refund request is for "
                            f"{requested_customer_id}. Do not process this refund."
                        ),
                    }
                })

        result = await self._session.call_tool(tool_name, tool_input)
        result_text = extract_tool_result_text(result)

        if tool_name == "get_customer":
            update_session_after_get_customer(result_text, session_state)

        return result_text


@asynccontextmanager
async def mcp_agent_tools():
    """Convenience wrapper around MCPAgentTools()."""
    client = MCPAgentTools()
    async with client:
        yield client
