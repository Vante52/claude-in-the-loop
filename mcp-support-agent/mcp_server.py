import json
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mock_data import CUSTOMERS, ORDERS

#loads .env
load_dotenv()

#Initialise the FastMCP server with a name
mcp = FastMCP("mcp-support-agent")
import anyio


#As we are using decorators, the docstring becomes the tool description
#FastMCP generates the input schema automatically from the args section and type annotations
#For more complex schemas, use pydantic models
@mcp.tool()
def get_customer(query: str) -> str:
    """
    Look up a customer record by name, email address, or customer ID.
    Use this tool when you need to verify who you are speaking with or
    retrieve account information. Returns the customer's full profile
    including account status, contact details, and a list of their order IDs.
    Do not use this tool to look up order details — use lookup_order for that.

    Args:
        query: The search term. Can be a full name (e.g. 'Sarah Chen'),
        an email address (e.g. 'sarah@email.com'),
        or a customer ID (e.g. 'CUST-4492').
    """
    query = query.strip().lower()

    for customer in CUSTOMERS.values():
        if (
            query == customer["customer_id"].lower()
            or query == customer["email"].lower()
            or query == customer["name"].lower()
        ):
            return json.dumps(customer)

    return json.dumps({
        "error": {
            "type": "validation",
            "retryable": False,
            "message": (
                f"No customer found matching '{query}'. The input may be "
                "misspelled or in the wrong format. Customer IDs follow the "
                "format CUST-XXXX. You can also search by full name or "
                "email address. Ask the customer to verify their details."
            )
        }
    })

@mcp.tool()
def lookup_order(order_id: str) -> str:
    """
    Look up a specific order by order ID. Use this tool when you need
    details about a particular order — status, items, shipping information,
    estimated delivery dates, or notes. Requires a valid order ID.
    To find a customer's order IDs, call get_customer first.

    Args:
        order_id: The order ID to look up. Must follow the format ORD-XXXX
        (e.g. 'ORD-8821'). This must be an exact match.
    """
    order_id = order_id.strip().upper()

    if order_id in ORDERS:
        return json.dumps(ORDERS[order_id])

    return json.dumps({
        "error": {
            "type": "validation",
            "retryable": False,
            "message": (
                f"No order found with ID '{order_id}'. "
                "Please check the order ID and try again."
            )
        }
    })

#Since the MCP server doesn't have access to the session state dictionary 
#Each call to the MCP server is stateless
@mcp.tool()
def process_refund(customer_id: str, order_id: str, amount: float) -> str:
    """
    Process a refund to the customer's original payment method.
    Requires a verified customer ID and a valid order ID.
    Only use this tool after get_customer has confirmed the customer's identity.

    Note: This tool validates order ownership server-side. Calling it with
    a customer_id that does not match the order will return a permission error.
    Session-level identity verification is enforced by the calling application.

    Args:
        customer_id: The verified customer ID from get_customer (e.g. 'CUST-4492').
        order_id: The order ID to refund (e.g. 'ORD-8821').
        amount: The refund amount in USD.
    """
    customer_id = customer_id.strip().upper()
    order_id = order_id.strip().upper()
    if order_id not in ORDERS:
        return json.dumps({
            "error": {
                "type": "validation",
                "retryable": False,
                "message": f"Order {order_id} not found."
            }
        })

    order = ORDERS[order_id]
    if order["customer_id"] != customer_id:
        return json.dumps({
            "error": {
                "type": "permission",
                "retryable": False,
                "message": (
                    f"Order {order_id} does not belong to customer {customer_id}."
                )
            }
        })

    return json.dumps({
        "success": True,
        "refund_id": "REF-" + order_id.split("-")[1],
        "customer_id": customer_id,
        "order_id": order_id,
        "amount": amount,
        "status": "initiated",
        "message": (
            f"Refund of ${amount:.2f} for order {order_id} has been initiated. "
            "Funds will return to the original payment method within 3-5 business days."
        )
})

#starts the server using stdio transport when the file is run directly
if __name__ == "__main__":
    mcp.run(transport="stdio")