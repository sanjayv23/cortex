from typing import TypedDict, Literal, List, Dict, Any

class ResearchState(TypedDict):
    topic: str
    research_notes: List[Dict[str, Any]]      # list of note dicts e.g. [{"sub_question": ..., "finding": ..., "source": ..., "url": ..., "confidence": ...}]
    draft: str
    draft_version: int
    editor_feedback: str
    final_report: str
    revision_count: int
    status: Literal["researching", "writing", "editing", "done"]

def create_initial_state(topic: str) -> ResearchState:
    """Create a fresh initial ResearchState dictionary."""
    return {
        "topic": topic,
        "research_notes": [],
        "draft": "",
        "draft_version": 0,
        "editor_feedback": "",
        "final_report": "",
        "revision_count": 0,
        "status": "researching",
    }
