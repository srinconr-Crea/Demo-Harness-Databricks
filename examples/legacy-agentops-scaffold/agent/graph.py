"""harness — LangGraph graph assembly.

Composes shared components into a compiled graph.
Edit tools.py to control tool selection.
"""

import os
import logging

from langgraph.graph import START, END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from databricks_langchain import ChatDatabricks
from tools import get_tools


logger = logging.getLogger(__name__)
LLM_ENDPOINT = os.environ.get("LLM_ENDPOINT", "databricks-claude-sonnet-5")



# --- Nodes ---

def agent_node(state: MessagesState) -> dict:
    """Call the LLM with tools bound."""
    tools = get_tools()
    llm = ChatDatabricks(endpoint=LLM_ENDPOINT)
    if tools:
        llm = llm.bind_tools(tools)
    response = llm.invoke(state["messages"])
    return {"messages": [response]}



def should_continue(state: MessagesState) -> str:
    """Route to tool_node if the last message has tool calls, otherwise end."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node"
    return END




# --- Graph ---

def build_graph():
    tools = get_tools()
    builder = StateGraph(MessagesState)


    builder.add_node("agent", agent_node)
    if tools:
        builder.add_node("tool_node", ToolNode(tools))


    builder.add_edge(START, "agent")


    if tools:
        builder.add_conditional_edges("agent", should_continue, {"tool_node": "tool_node", END: END})
        builder.add_edge("tool_node", "agent")
    else:
        builder.add_edge("agent", END)

    return builder


# Export builder for per-request compilation with checkpointer
graph_builder = build_graph()

# Compiled graph without checkpointer (used at startup, fallback)
graph = graph_builder.compile()
