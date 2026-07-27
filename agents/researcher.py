import sys
from typing import List, Optional, Dict, Any

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from pydantic import BaseModel, Field

from state import ResearchState
from db.vector_store import query_vector_store
from utils.llm import call_llm_json

RESEARCHER_SYSTEM_PROMPT = """You are a meticulous research agent. Given a topic, you decompose it into
sub-questions, retrieve evidence, and produce structured notes. You never
state a claim without attaching the source it came from. If evidence is
thin or conflicting, say so explicitly rather than filling the gap with
assumption. Output strictly as JSON matching the ResearchNote schema."""

class SubQuestionsSchema(BaseModel):
    sub_questions: List[str] = Field(description="List of 3 to 5 clear sub-questions exploring the topic.")

class ResearchNoteItem(BaseModel):
    sub_question: str = Field(description="The sub-question being addressed.")
    finding: str = Field(description="Synthesized factual finding answering the sub-question based strictly on retrieved evidence.")
    source: str = Field(description="The source ID from which this finding was retrieved (e.g. SRC_01, WEB_SRC_01).")
    url: Optional[str] = Field(default="N/A", description="URL or reference path of the source.")
    confidence: str = Field(default="High", description="Confidence level: High, Medium, or Low based on evidence strength.")

class ResearchNotesSchema(BaseModel):
    notes: List[ResearchNoteItem] = Field(description="List of grounded research notes with citations.")

def researcher_node(state: ResearchState) -> Dict[str, Any]:
    """
    Researcher Node:
    1. Break topic into sub-questions.
    2. Query vector store / fallback web search for evidence for each sub-question.
    3. Synthesize evidence into structured ResearchNotes dicts.
    """
    topic = state["topic"]
    print(f"\n🔍 [AGENT 1: RESEARCHER] Analyzing topic: '{topic}'")

    # Step 1: Generate sub-questions
    user_prompt_sq = f"Decompose the following research topic into 3 to 5 sub-questions: '{topic}'."
    try:
        sq_output = call_llm_json(
            system_prompt=RESEARCHER_SYSTEM_PROMPT,
            user_prompt=user_prompt_sq,
            output_schema=SubQuestionsSchema
        )
        sub_questions = sq_output.sub_questions
    except Exception as e:
        print(f"⚠️ OpenAI API call failed or unavailable ({e}). Utilizing heuristic sub-questions.")
        sub_questions = [
            f"What is the foundational background, core definitions, and mechanisms of {topic}?",
            f"What are the primary applications, empirical impacts, and recent developments regarding {topic}?",
            f"What are the key challenges, policy or structural implications, and future outlook for {topic}?"
        ]


    print(f"📋 Generated Sub-Questions ({len(sub_questions)}):")
    for idx, sq in enumerate(sub_questions, 1):
        print(f"   {idx}. {sq}")

    # Step 2: Retrieve evidence for each sub-question
    all_retrieved_evidence = []
    for sq in sub_questions:
        hits = query_vector_store(sq, n_results=3)
        for h in hits:
            all_retrieved_evidence.append({
                "sub_question": sq,
                "content": h["content"],
                "source_id": h["source_id"],
                "url": h["url"],
                "title": h["title"]
            })

    # Step 3: Synthesize into structured notes using LLM
    synthesis_user_prompt = (
        f"Topic: {topic}\n\n"
        f"Retrieved Evidence:\n"
    )
    for idx, ev in enumerate(all_retrieved_evidence, 1):
        synthesis_user_prompt += (
            f"[{idx}] Sub-Question: {ev['sub_question']}\n"
            f"    Source ID: {ev['source_id']}\n"
            f"    URL: {ev['url']}\n"
            f"    Content snippet: {ev['content']}\n\n"
        )

    synthesis_user_prompt += (
        "Instructions: Synthesize the evidence above into a list of structured research notes.\n"
        "EVERY finding MUST attach the exact source ID it came from. If no evidence supports a claim, omit it."
    )

    try:
        notes_output = call_llm_json(
            system_prompt=RESEARCHER_SYSTEM_PROMPT,
            user_prompt=synthesis_user_prompt,
            output_schema=ResearchNotesSchema
        )
        notes_dicts = [item.model_dump() for item in notes_output.notes]
    except Exception as e:
        print(f"⚠️ Synthesis fallback due to LLM error: {e}")
        notes_dicts = []
        for ev in all_retrieved_evidence:
            notes_dicts.append({
                "sub_question": ev["sub_question"],
                "finding": ev["content"],
                "source": ev["source_id"],
                "url": ev["url"],
                "confidence": "Medium"
            })

    print(f"✅ Researcher produced {len(notes_dicts)} grounded notes.")

    return {
        "research_notes": notes_dicts,
        "status": "writing"
    }
