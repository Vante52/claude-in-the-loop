# Load environment variables from .env file
from dotenv import load_dotenv
# Official anthropic client library
from anthropic import Anthropic
# MCP client: connects to mcp_server.py and runs tools with session gates
from mcp_client import MCPAgentTools

from typing import Any

import anyio

# Load environment variables into the runtime
load_dotenv()

# System prompt that defines the agent's behavior, constraints, and workflow
SYSTEM_PROMPT = """You are a customer support agent for an online retailer.
You have access to tools that let you look up customer records, order details,
and process refunds.

When a customer contacts you:
1. Always look up their account using get_customer before doing anything else.
2. Use lookup_order to get details on any specific order they mention.
3. Only process refunds after you have verified the customer's identity with get_customer. The system will block refunds attempted before verification.
4. Give clear, helpful responses based on what you find.
5. If you cannot find a customer or order, tell them politely and ask them to double-check the information they provided.

Always verify who you are speaking with before discussing account details
or processing any financial transactions."""

# Create real agent with session memory, gates, MCP client, settings and history
class SupportAgent:
    def __init__(self, mcp_tools: MCPAgentTools, model: str="claude-sonnet-4-6", max_tokens: int= 1024) -> None:
        # Initialize anthropic client
        self.client = Anthropic()
        self.mcp_tools = mcp_tools
        self.model = model
        self.max_tokens = max_tokens
        self.conversation_history: list[dict[str, Any]] = []
        self.session_state: dict[str, Any] = {
            "verified_customer_id": None,
            "verified_customer_name": None,
        }


    
    #Core agent loop with MCP-backed tools.
    async def run_turn(self, user_message: str) -> str:
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        tool_round = 0

        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                tools=self.mcp_tools.anthropic_tools,
                messages=self.conversation_history,
            )
            
            self.conversation_history.append({
                "role": "assistant",
                "content": response.content,
            })

            if response.stop_reason == "end_turn":
                return self._extract_text(response.content)

            if response.stop_reason != "tool_use":
                return self._extract_text(response.content)

            tool_results = await self._run_requested_tools(response.content)

            self.conversation_history.append({
                "role": "user",
                "content": tool_results,
            })

    async def _run_requested_tools(self, content_blocks: list[Any]) -> list[dict[str, Any]]:
        tool_results = []

        for block in content_blocks:
            if getattr(block, "type", None) != "tool_use":
                continue

            result = await self.mcp_tools.run_tool(
                tool_name=block.name,
                tool_input=block.input,
                session_state=self.session_state,
            )

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        return tool_results

    def _extract_text(self, content_blocks: list[Any]) -> str:
        text_parts = []

        for block in content_blocks:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
            elif hasattr(block, "text"):
                text_parts.append(block.text)

        return "\n".join(text_parts)

    def reset_session(self) -> None:
        self.conversation_history = []
        self.session_state = {
            "verified_customer_id": None,
            "verified_customer_name": None,
        }


async def main() -> None:
    #One MCP server subprocess is started per conversation and kept alive until the agent returns a final answer to the user.
    async with MCPAgentTools() as mcp_tools:
        agent = SupportAgent(mcp_tools)

        print("Customer Support Agent (MCP)")
        print("Type 'quit' to exit")
        print("=" * 40)

        while True:
            user_input = input("\nCustomer: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                break

            if user_input.lower() in ("reset", "new session"):
                agent.reset_session()
                print("\nAgent: Session reset.")
                continue

            print("\nAgent:", end=" ", flush=True)
            response = await agent.run_turn(user_input)
            print(response)


if __name__ == "__main__":
    anyio.run(main)   
