from typing import Literal
from langgraph.graph import StateGraph, END
from state import ResearchState
from agents.researcher import researcher_node
from agents.writer import writer_node
from agents.editor import editor_node

def route_from_editor(state: ResearchState) -> Literal["writer", "__end__"]:
    """
    Conditional routing function from editor node.
    If status == 'done', terminate graph execution (END).
    Otherwise, return 'writer' for revision pass.
    """
    status = state.get("status", "done")
    if status == "done":
        return END
    return "writer"

def build_research_graph():
    """Build and compile the LangGraph StateGraph pipeline."""
    builder = StateGraph(ResearchState)

    # Add nodes
    builder.add_node("researcher", researcher_node)
    builder.add_node("writer", writer_node)
    builder.add_node("editor", editor_node)

    # Entry point and static edges
    builder.set_entry_point("researcher")
    builder.add_edge("researcher", "writer")
    builder.add_edge("writer", "editor")

    # Conditional edge from editor
    builder.add_conditional_edges(
        "editor",
        route_from_editor,
        {
            "writer": "writer",
            END: END
        }
    )

    return builder.compile()

# Default compiled graph instance
pipeline_graph = build_research_graph()
