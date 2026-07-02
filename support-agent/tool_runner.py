import json
#Import mock datasets that simulate a database
from mock_data import CUSTOMERS, ORDERS

#Fetch a customer by matching against multiple possible identifiers
def get_customer(query:str, session_state:dict) -> str:
    #Normalize input for consistent matching (ignore case + extra spaces)
    query = query.strip().lower()
    
    #iterate through all customers in the dataset
    for customer in CUSTOMERS.values():
        #Match against customer ID, name, or email
        #This makes the tool  flexible in how it can be called
        if(
            query == customer["customer_id"].lower() or
            query == customer["name"].lower() or
            query == customer["email"].lower()
        ):
            # Write verified identity into session state before returning.
            # This is what downstream gates check — if these values are set,
            # it means this function ran successfully and found a real customer.
            session_state["verified_customer_id"] = customer["customer_id"]
            session_state["verified_customer_name"] = customer["name"]
            #Return the customer record as a JSON string for easy consumption
            return json.dumps(customer)
    #if no match is found, return a structured error response
    return json.dumps({
        "error": 
            {
                "type" : "validation",
                "retryable" : False,
                "message" : (f"Customer not found: No customer record found matching '{query}'. Ask the customer to check information. Consider customer ID format should follow 'CUST-XXXX' or try to check by name or email address")
            }
    })



#Fetch an order using its order ID
def lookup_order(order_id:str, session_state:dict)->str:
    #normalize input for consistent matching (ignore case + extra spaces)
    order_id = order_id.strip().upper()
    
    #Check if the order ID exists in the dataset
    if order_id in ORDERS:
        #Return the order record as a JSON string for easy consumption
        return json.dumps(ORDERS[order_id])
    #if no match is found, return a structured error response
    return json.dumps({
        "error": 
            {
                "type" : "validation",
                "retryable" : False,
                "message" : ( "Order not found:" 
                            f"No order record found matching '{order_id}'."
                            "If order ID is not listed in customer information, order does not belong to the customer."
                            "Ask the user to check the order ID format (e.g. 'ORD-XXXX').")
            }
    })

def process_refund(customer_id: str, order_id: str, amount: float, session_state: dict) -> str:

    # Gate check 1: Has identity verification happened at all?
    # session_state["verified_customer_id"] is None until get_customer
    # runs successfully. If it's still None, the conversation hasn't
    # gone through verification and we block unconditionally.
    if not session_state.get("verified_customer_id"):
        return json.dumps({
            "error": {
                "type": "permission",
                "retryable": False,
                "message": (
                    "Cannot process a refund before customer identity has been "
                    "verified. Call get_customer first and confirm the customer's "
                    "identity before attempting a refund."
                )
            }
        })

    # Gate check 2: Does the customer_id Claude is trying to refund
    # match the customer who was actually verified in this session?
    # This prevents a subtle but serious bug: if Claude somehow has the
    # wrong customer_id — from a previous message, a misread, or anything
    # else — this check catches it before money moves.
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
                )
            }
        })

    # Both gates passed. Now do the actual work.

    # Check the order exists before attempting the refund
    if order_id not in ORDERS:
        return json.dumps({
            "error": {
                "type": "validation",
                "retryable": False,
                "message": (
                    f"Order {order_id} not found. Verify the order ID with the "
                    "customer and try again."
                )
            }
        })

    # Verify the order belongs to the verified customer.
    # Without this check, a verified customer could potentially
    # request a refund on someone else's order ID.
    order = ORDERS[order_id]
    if order["customer_id"] != session_state["verified_customer_id"]:
        return json.dumps({
            "error": {
                "type": "permission",
                "retryable": False,
                "message": (
                    f"Order {order_id} does not belong to the verified customer. "
                    "Do not process this refund."
                )
            }
        })

    # All checks passed — simulate the refund
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
    
#Central dispatcher that routes tool calls to the correct function based on the tool name
def run_tool(tool_name: str, tool_input: dict) -> str:
    #Route to the appropriate tool based on its name
    if tool_name == "get_customer":
        #Expecting "query" in tool_input
        return get_customer(tool_input["query"])
    
    elif tool_name == "lookup_order":
        #Expecting "order_id" in tool_input
        return lookup_order(tool_input["order_id"])

    elif tool_name == "process_refund":
        return process_refund(tool_input["customer_id"], tool_input["order_id"], tool_input["amount"])
    
    else:
        #Handle unknown toll calls safety with a structured error message
        return json.dumps({
            "error": "validation",
            "message": f"The tool '{tool_name}' is not recognized. "
        })