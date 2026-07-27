import sys
import json
from typing import Dict, Any

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from pydantic import BaseModel, Field

from state import ResearchState
from utils.llm import call_llm_json

WRITER_SYSTEM_PROMPT = """You are an elite, highly detailed technical writer and research analyst. You turn structured research
notes into an in-depth, comprehensive research report with inline citations. You write multi-paragraph sections that synthesize evidence, provide thorough context, explain mechanisms, analyze implications, and detail empirical findings. You never introduce ungrounded claims. When given editor feedback, you revise surgically while preserving all detailed sections."""

class DraftSchema(BaseModel):
    title: str = Field(description="Title of the comprehensive research report.")
    markdown_draft: str = Field(description="Complete Markdown document with title, executive summary, background context, detailed sub-question analysis, strategic implications, conclusion, inline numerical citations [1], [2], and a formatted References / Sources section at the bottom.")

def writer_node(state: ResearchState) -> Dict[str, Any]:
    """
    Writer Node:
    Takes research_notes (and editor_feedback if revision_count > 0)
    and generates an in-depth, structured markdown draft report.
    """
    topic = state["topic"]
    notes = state.get("research_notes", [])
    editor_feedback = state.get("editor_feedback", "")
    current_version = state.get("draft_version", 0) + 1

    print(f"\n✍️ [AGENT 2: WRITER] Drafting Comprehensive Report Version v{current_version} (Revision count: {state.get('revision_count', 0)})")

    notes_formatted = json.dumps(notes, indent=2)

    if editor_feedback:
        user_prompt = (
            f"Topic: {topic}\n\n"
            f"Current Draft Version: v{state.get('draft_version', 1)}\n"
            f"Previous Draft:\n{state.get('draft', '')}\n\n"
            f"EDITOR FEEDBACK TO ADDRESS:\n{editor_feedback}\n\n"
            f"Research Notes Reference:\n{notes_formatted}\n\n"
            "Instructions: Revise the draft report surgically to address every point in the editor feedback. "
            "Do NOT shorten or discard unflagged sections. Maintain strict inline citations matching sources in notes."
        )
    else:
        user_prompt = (
            f"Topic: {topic}\n\n"
            f"Research Notes:\n{notes_formatted}\n\n"
            "Instructions:\n"
            "Produce an in-depth, comprehensive technical report with:\n"
            "1. Clear Executive Title & Executive Summary\n"
            "2. Background & Domain Context\n"
            "3. Multi-paragraph Detailed Sections analyzing each sub-question from notes\n"
            "4. Strategic Implications & Policy Outlook\n"
            "5. Conclusion\n"
            "6. Inline numerical citations [1], [2] matching claims to research note sources.\n"
            "7. A References list at the end detailing Source ID, Title, and URL."
        )

    try:
        draft_output = call_llm_json(
            system_prompt=WRITER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            output_schema=DraftSchema
        )
        draft_text = draft_output.markdown_draft
    except Exception as e:
        print(f"⚠️ Writer LLM call failed or unavailable ({e}). Generating detailed fallback report structure.")
        # Fallback comprehensive structured report generation
        topic_title = topic.strip().title()
        draft_text = f"# Comprehensive Research Report: {topic_title}\n\n"
        draft_text += "## Executive Summary\n"
        draft_text += (
            f"This research report provides a detailed, multi-dimensional analysis of **{topic}**. "
            f"Based on empirical evidence and retrieved source materials, this study examines core mechanisms, "
            f"current developments, structural shifts, and strategic policy implications.\n\n"
        )
        
        draft_text += "## Background & Context\n"
        draft_text += (
            f"The study of {topic} has emerged as a key focal point across technical, economic, and institutional domains. "
            f"Understanding its underlying dynamics requires analyzing evidence from multiple primary sources and vector indices.\n\n"
        )
        
        draft_text += "## Empirical Findings & Sub-Question Analysis\n\n"
        
        # Group notes by sub-question for detailed multi-paragraph reporting
        grouped_notes = {}
        for note in notes:
            sq = note.get("sub_question", "General Sub-Question")
            if sq not in grouped_notes:
                grouped_notes[sq] = []
            grouped_notes[sq].append(note)
            
        citation_idx = 1
        citation_references = []
        
        for sq, note_list in grouped_notes.items():
            draft_text += f"### {sq}\n"
            for n in note_list:
                finding = n.get("finding", "").strip()
                source = n.get("source", "SRC_01")
                url = n.get("url", "N/A")
                conf = n.get("confidence", "High")
                
                draft_text += f"{finding} [{citation_idx}]\n\n"
                draft_text += f"*Analytical Note*: Evidence strength evaluated as **{conf}** confidence based on source `{source}`.\n\n"
                
                citation_references.append({
                    "idx": citation_idx,
                    "source": source,
                    "url": url,
                    "sq": sq
                })
                citation_idx += 1
                
        draft_text += "## Strategic Implications & Future Outlook\n"
        draft_text += (
            f"The empirical evidence regarding {topic} indicates significant ongoing structural developments. "
            f"Organizations, policymakers, and industry stakeholders should monitor key performance metrics, "
            f"regulatory adaptations, and technological shifts to optimize future strategic decision-making.\n\n"
        )
        
        draft_text += "## Conclusion\n"
        draft_text += (
            f"In conclusion, this report demonstrates that {topic} encompasses complex, multi-faceted dimensions. "
            f"All findings presented are grounded strictly in retrieved source documentation.\n\n"
        )
        
        draft_text += "## References & Source Citations\n"
        for ref in citation_references:
            draft_text += f"[{ref['idx']}] **{ref['source']}** — {ref['url']}\n"


    print(f"✅ Draft Version v{current_version} created ({len(draft_text)} characters).")

    return {
        "draft": draft_text,
        "draft_version": current_version,
        "status": "editing"
    }
