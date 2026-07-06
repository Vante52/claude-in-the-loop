<h1 align="center">───── ⋅•⋅⊰∙∘☽ MCP Support Agent ☾∘∙⊱⋅•⋅ ─────</h1>

<p align="center"><sub><em>A small but complete customer-support agent built with <strong>Claude</strong>, <strong>MCP</strong>, and <strong>Python</strong>.</em></sub></p>

<p align="center">
<img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
<img alt="MCP" src="https://img.shields.io/badge/Protocol-MCP-6E56CF">
<img alt="Claude" src="https://img.shields.io/badge/Model-Claude-D97757?logo=anthropic&logoColor=white">
<img alt="Lab" src="https://img.shields.io/badge/Status-MCP%20Playground-ff69b4">

<p align="center">⋅•⋅⊰∙∘☽༓☾∘∙⊱⋅•⋅</p>

This project shows how to migrate from a local `tools.py + tool_runner.py` setup into a cleaner MCP architecture:

&nbsp;&nbsp;⊹ `mcp_server.py` exposes tools through the Model Context Protocol.<br>
&nbsp;&nbsp;⊹ `mcp_client.py` discovers and calls those tools.<br>
&nbsp;&nbsp;⊹ `agent.py` talks to Claude, keeps conversation state, and applies session gates.<br>
&nbsp;&nbsp;⊹ `mock_data.py` acts as a tiny fake database while learning.<br>

> Think of it as a support agent playground: small enough to understand, but structured like a real agent.


<h2 align="center"> ⋙════ ⊹ ⊱꒰⋆ Architecture ⋆꒱⊰ ⊹ ════ ⋘</h2>

The project follows the standard MCP architecture detailed in the wiki:

TODO: diagrama

In MCP terms:

| File | Role |
|---|---|
| `agent.py` | AI host / agent |
| `mcp_client.py` | MCP client |
| `mcp_server.py` | MCP server |
| `mock_data.py` | Fake external system / database |


<h2 align="center"> ⋙════ ⊹ ⊱꒰⋆ Folder Structure ⋆꒱⊰ ⊹ ════ ⋘</h2>

```text
mcp-support-agent/
├── agent.py
├── mcp_client.py
├── mcp_server.py
├── mock_data.py
├── requirements.txt
├── .env
└── .claude/
    └── mcp.json
```

<h2 align="center"> ⋙════ ⊹ ⊱꒰⋆ File Guide ⋆꒱⊰ ⊹ ════ ⋘</h2>

### `agent.py`

This is the actual Claude agent.

It is responsible for:

&nbsp;&nbsp;⊹ Calling the Claude Messages API<br>
&nbsp;&nbsp;⊹ Keeping `conversation_history`<br>
&nbsp;&nbsp;⊹ Keeping `session_state`<br>
&nbsp;&nbsp;⊹ Sending MCP-discovered tools to Claude<br>
&nbsp;&nbsp;⊹ Receiving `tool_use` blocks from Claude<br>
&nbsp;&nbsp;⊹ Returning tool results back to Claude<br>
&nbsp;&nbsp;⊹ Running a CLI conversation loop<br>

The agent is implemented as a class so it does not forget everything after every user message.

```text
SupportAgent
├── conversation_history
├── session_state
├── mcp_tools
├── model settings
└── run_turn()
```

---

### `mcp_client.py`

This replaces the old local `tool_runner.py`.

It is responsible for:

&nbsp;&nbsp;⊹ Starting `mcp_server.py` as a subprocess<br>
&nbsp;&nbsp;⊹ Connecting to it over stdio<br>
&nbsp;&nbsp;⊹ Discovering tools with `list_tools()`<br>
&nbsp;&nbsp;⊹ Converting MCP tool schemas to Anthropic tool schemas<br>
&nbsp;&nbsp;⊹ Calling tools with `call_tool()`<br>
&nbsp;&nbsp;⊹ Applying session gates before sensitive tool calls<br>
&nbsp;&nbsp;⊹ Updating `session_state` after successful customer verification<br>

Important idea:

```text
tools.py        → replaced by MCP list_tools()
tool_runner.py  → replaced by MCPAgentTools.run_tool()
```

---

### `mcp_server.py`

This is the MCP server.

It exposes the support tools:

&nbsp;&nbsp;⊹ `get_customer`<br>
&nbsp;&nbsp;⊹ `lookup_order`<br>
&nbsp;&nbsp;⊹ `process_refund`<br>

The tools are registered with:

```python
@mcp.tool()
```

FastMCP uses the function name, type annotations, and docstrings to generate the tool definition automatically. That means you do not need to manually write a JSON schema for every tool.

---

### `mock_data.py`

This is a fake database.

It contains hardcoded customers and orders so the agent can be tested without connecting to a real backend.

In a real project, this file would usually be replaced by:

&nbsp;&nbsp;⊹ a database<br>
&nbsp;&nbsp;⊹ an internal API<br>
&nbsp;&nbsp;⊹ a CRM<br>
&nbsp;&nbsp;⊹ Shopify<br>
&nbsp;&nbsp;⊹ Stripe<br>
&nbsp;&nbsp;⊹ a support-ticketing system<br>
&nbsp;&nbsp;⊹ another MCP server<br>

> ⚠️ Do **not** store secrets in `mock_data.py`. Secrets belong in `.env` or in environment variables passed only to the process that actually needs them.

---

### `.claude/mcp.json`

This file is useful for tools like Claude Code. It tells a compatible MCP host how to start your MCP server.

Example:

```json
{
  "mcpServers": {
    "support-agent-tools": {
      "command": "python3",
      "args": ["mcp_server.py"],
      "cwd": "${workspaceFolder}/mcp-support-agent"
    }
  }
}
```

> This file does **not** automatically connect your custom `agent.py` to the MCP server. Your Python agent uses `mcp_client.py` for that.

&nbsp;&nbsp;⊹ Use `.claude/mcp.json` when you want Claude Code or another MCP-compatible host to discover and use your server.<br>
&nbsp;&nbsp;⊹ Use `mcp_client.py` when you want your own Python agent to connect to the server.<br>

<h2 align="center"> ⋙════ ⊹ ⊱꒰⋆ Requirements ⋆꒱⊰ ⊹ ════ ⋘</h2>

You need:

&nbsp;&nbsp;⊹ Python 3.10+<br>
&nbsp;&nbsp;⊹ Node.js 22+ if you want to use the MCP Inspector<br>
&nbsp;&nbsp;⊹ An Anthropic API key<br>

Install Python dependencies from `requirements.txt`. Current dependencies:

```txt
mcp[cli]>=1.28.1,<2
anthropic>=0.116.0,<1
python-dotenv>=1.2.2,<2
```

<h2 align="center"> ⋙════ ⊹ ⊱꒰⋆ Setup ⋆꒱⊰ ⊹ ════ ⋘</h2>

Clone or enter the project folder:

```bash
cd path/to/mcp-support-agent
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Create a `.env` file:

```bash
touch .env
```

Add your Anthropic API key:

```env
ANTHROPIC_API_KEY=your_api_key_here
```

Make sure `.env` is in your `.gitignore`:

```gitignore
.env
.venv/
__pycache__/
```

> 🔒 Never commit API keys.


<h2 align="center"> ⋙════ ⊹ ⊱꒰⋆ Test the MCP Server with the Inspector ⋆꒱⊰ ⊹ ════ ⋘</h2>

The MCP Inspector lets you test the server without running the Claude agent.

Run:

```bash
npx @modelcontextprotocol/inspector python3 mcp_server.py
```

Open the Inspector UI in your browser, connect to the server, and try calling `get_customer` with:

```json
{
  "query": "Sarah Chen"
}
```

You should receive Sarah's customer record as JSON.

Try a failing lookup too:

```json
{
  "query": "nobody@fake.com"
}
```

You should receive a structured error response.

If both work, your MCP server is working. 

<h2 align="center"> ⋙════ ⊹ ⊱꒰⋆ Run the Agent ⋆꒱⊰ ⊹ ════ ⋘</h2>

Start the support agent:

```bash
python agent.py
```

You should see:

```text
Customer Support Agent (MCP)
Type 'quit' to exit
========================================
```

Try:

```text
Hi, my name is Sarah Chen and my order number is ORD-8821.
I placed it six days ago and it still hasn't shipped. Can you help?
```

The expected flow is:

```text
User asks for help
→ Claude decides it needs customer data
→ agent.py receives tool_use
→ mcp_client.py calls mcp_server.py
→ get_customer returns Sarah's data
→ session_state stores verified_customer_id
→ Claude may call lookup_order
→ agent responds with order details
```

To reset the conversation: `reset` · To exit: `quit`


<h2 align="center"> ⋙════ ⊹ ⊱꒰⋆ Example Test Prompts ⋆꒱⊰ ⊹ ════ ⋘</h2>

### 1. Customer with an existing order

```text
Hi, my name is Sarah Chen and my order number is ORD-8821.
I placed it six days ago and it still hasn't shipped. Can you help?
```

**Expected behavior:** the agent verifies Sarah with `get_customer`, looks up `ORD-8821`, and explains the order status and notes.

---

### 2. Invalid order

```text
Hi, I'm Sarah Chen. I need help with order ORD-1234.
```

**Expected behavior:** the agent verifies Sarah, tries to look up the order, the MCP server returns a structured validation error, and the agent politely asks the customer to double-check the order ID.

---

### 3. Valid customer with no orders

```text
Hi, I'm James Okafor. I'm trying to check on my recent orders.
```

**Expected behavior:** the agent verifies James, sees that the account exists, and explains that there are no orders on the account.

---

### 4. Refund request without identity

```text
I want a refund on order ORD-8821 for $79.99.
```

**Expected behavior:** the agent should not process the refund immediately — it should ask for customer identity first. If Claude tries to call `process_refund` too early, the MCP client gate blocks it.

---

### 5. Refund request with identity

```text
Hi, I'm Sarah Chen. I'd like a refund on order ORD-8821 for $79.99.
```

**Expected behavior:** the agent calls `get_customer`, `session_state` stores Sarah's verified customer ID, the agent calls `process_refund`, the MCP server validates that the order belongs to Sarah, and the refund is initiated.

<h2 align="center"> ⋙════ ⊹ ⊱꒰⋆ Common Issues ⋆꒱⊰ ⊹ ════ ⋘</h2>

<details>
<summary><strong>ANTHROPIC_API_KEY not found</strong></summary>
<br>

Make sure your `.env` file exists and contains:

```env
ANTHROPIC_API_KEY=your_api_key_here
```

Also make sure `agent.py` calls:

```python
load_dotenv()
```

</details>

<details>
<summary><strong>MCP Inspector does not start</strong></summary>
<br>

Check Node.js:

```bash
node --version
npx --version
```

Use a recent Node.js version.

</details>

<details>
<summary><strong>Python import errors</strong></summary>
<br>

Make sure your virtual environment is active:

```bash
source .venv/bin/activate
```

Then reinstall dependencies:

```bash
python3 -m pip install -r requirements.txt
```

</details>

<details>
<summary><strong>The agent forgets the customer</strong></summary>
<br>

Make sure the CLI creates one `SupportAgent` and keeps it alive for the whole conversation. Do not recreate `session_state` on every user message.

</details>

<h2 align="center"> ⋙════ ⊹ ⊱꒰⋆ Next Steps ⋆꒱⊰ ⊹ ════ ⋘</h2>

&nbsp;&nbsp;⊹ Add a real database instead of `mock_data.py`<br>
&nbsp;&nbsp;⊹ Add logging for every tool call<br>
&nbsp;&nbsp;⊹ Add automated tests<br>
&nbsp;&nbsp;⊹ Add more tools, such as `cancel_order` or `update_shipping_address`<br>
&nbsp;&nbsp;⊹ Add human approval before refunds<br>
&nbsp;&nbsp;⊹ Add a richer CLI or web UI<br>
&nbsp;&nbsp;⊹ Split MCP servers by domain, such as `customers`, `orders`, and `payments`<br>

<h2 align="center"> ⋙════ ⊹ ⊱꒰⋆ Summary ⋆꒱⊰ ⊹ ════ ⋘</h2>

This project is a small but realistic MCP support agent. It shows the core migration:

```text
From:
tools.py + tool_runner.py

To:
mcp_server.py + mcp_client.py
```

The final architecture keeps things clean:

```text
agent.py keeps the conversation
mcp_client.py manages MCP calls and gates
mcp_server.py exposes reusable tools
mock_data.py simulates external data
```

<blockquote>
<p align="center"><strong><em>Small project. Big agent architecture lesson.</em></strong></p>
</blockquote>

<p align="center">⋅•⋅⊰∙∘☽༓☾∘∙⊱⋅•⋅</p>