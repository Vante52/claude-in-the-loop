#Load enviroment variables from .env file
from dotenv import load_dotenv
#Official anthropic client library
from anthropic import Anthropic
#Tool definitions (what Claude is allowed to use)
from tools import tools
#Local excecution layer for actually running tools
from tool_runner import run_tool

#Load environment variables into the runtime
load_dotenv()

#Initialize anthropic client
client = Anthropic()

#System prompt that defines the agent's behaivor, constraints, and workflow
SYSTEM_PROMPT = """You are a customer support agent for an online retailer.
You have access to tools that let you look up costumer records and order details.

When a costumer contacts you:
1. Look up their acciount using get_customer before doing anithing else.
2. Use lookup_order to get details on any specific order they mention.
3. Give clear, helful responses based in what you find.
4. If you cannot find a costumer or order, tell them politely and ask them to double check the information they provided.

Allways verify who you are speaking with before discussing account details.
"""
#Core agent loop: takes an user message and returns a final response
def run_agent(user_message:str)->str:
    #Initialize conversation history with the user's first message
    conversation_history = [
        {"role": "user", "content": user_message}
    ]
    # Session state tracks verified identity and anything else
    # that needs to persist across tool calls within this conversation.
    # It starts empty and gets populated as tools run successfully.
    session_state = {
        "verified_customer_id": None,
        "verified_customer_name": None
    }
    
    #Loop until Claude finishes the interaction
    while True:
        #send current state (history + tools + system promt) to Claude
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system = SYSTEM_PROMPT,
            tools = tools,
            messages = conversation_history
        )
        
        #Always append Claude's response inmediately
        #This preserves the full chain: assistant -> tool call -> tool result -> next turn
        conversation_history.append({
            "role": "assistant",
            "content": response.content
        })
        
        #If claude has finished responding (no more tool calls)
        if response.stop_reason == "end_turn":
            #Extract and return the text response from content blocks
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            #Fallback in case no text block is found
            return ""
        
        #If Claude wants to use tools
        if response.stop_reason == "tool_use":
            tool_results = []
            
            #Iterate through all tool calls in the response
            for block in response.content:
                if block.type == "tool_use":
                    #Excecute the tool locally with provided inputs
                    result = run_tool(block.name, block.input, session_state)
                    #Collect tool results in the required format
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            
            #Send all tool results back in a single user message
            #This allows Claude to continue reasoning with fresh data
            conversation_history.append({
                "role":"user",
                "content": tool_results
            })
            
#Entry point for running the agent in a CLI Loop
if __name__ == "__main__":
    print("Customer Support Agent, Stage 1")
    print("Type 'quit' to exit")
    print("=" * 40)
    
    while True:
        #Read user input from terminal
        user_input = input("\nCustomer: ").strip()
        
        #Ignore empry input from terminal
        if not user_input:
            continue
        
        #Exit conditions
        if user_input.lower() in ("quit", "exit", "q"):
            break
        
        #Print agent response (stream-like UX with flush)
        print("\nAgent:", end= " ", flush= True)
        response = run_agent(user_input)
        print (response)