import os
import sys
import time
import argparse

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from state import create_initial_state

from graph import pipeline_graph
from db.vector_store import get_or_create_collection
from ingest import ingest_directory
from utils.logger import RunLogger

def run_pipeline(topic: str, docs_dir: str = "./docs", auto_ingest: bool = True):
    print("=" * 80)
    print(f"🚀 MULTI-AGENT RESEARCH PIPELINE")
    print(f"📌 Topic: '{topic}'")
    print("=" * 80)

    # Step 1: Ensure ChromaDB collection is populated
    collection = get_or_create_collection()
    if collection.count() == 0:
        print("ℹ️ ChromaDB collection 'research_sources' is empty.")
        if auto_ingest:
            print(f"📥 Automatically ingesting documents from '{docs_dir}'...")
            ingest_directory(docs_dir)
        else:
            print("⚠️ Warning: Collection is empty. Researcher agent will use web search fallback.")
    else:
        print(f"📚 Vector DB contains {collection.count()} document chunks ready for retrieval.")

    # Initialize logger
    logger = RunLogger(topic=topic)

    # Initialize state
    initial_state = create_initial_state(topic)
    logger.log_step("init", "initialized", {"initial_state": initial_state})

    start_time = time.time()

    # Step 2: Stream / Execute LangGraph StateGraph
    print("\n⚡ Executing LangGraph pipeline nodes...")
    final_state = initial_state

    # We can stream step outputs from LangGraph to capture each node transition
    for event in pipeline_graph.stream(initial_state):
        for node_name, state_update in event.items():
            print(f"➡️ Node completed: [{node_name.upper()}]")
            # Update running final_state tracking
            for key, val in state_update.items():
                final_state[key] = val

            logger.log_step(
                step_name=node_name,
                status=state_update.get("status", "in_progress"),
                details={
                    "draft_version": state_update.get("draft_version", final_state.get("draft_version")),
                    "revision_count": state_update.get("revision_count", final_state.get("revision_count")),
                    "editor_feedback": state_update.get("editor_feedback", ""),
                    "notes_count": len(final_state.get("research_notes", [])),
                    "draft_snippet": state_update.get("draft", "")[:200] if state_update.get("draft") else ""
                }
            )

    elapsed = time.time() - start_time
    final_report = final_state.get("final_report", final_state.get("draft", "No report generated."))

    logger.finalize(final_report)

    # Save report to ./reports/
    os.makedirs("./reports", exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join("./reports", f"report_{timestamp}.md")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(final_report)

    print("\n" + "=" * 80)
    print(f"✨ PIPELINE COMPLETE (Execution time: {elapsed:.2f}s)")
    print(f"📄 Final report saved to: {os.path.abspath(report_file)}")
    print(f"📊 Draft Versions: {final_state.get('draft_version', 1)} | Revision Loops: {final_state.get('revision_count', 0)}")
    print("=" * 80)
    print("\n" + final_report)
    print("\n" + "=" * 80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Multi-Agent Research Pipeline")
    parser.add_argument("--topic", type=str, required=True, help="Research topic string")
    parser.add_argument("--docs_dir", type=str, default="./docs", help="Path to source docs directory")
    parser.add_argument("--no_auto_ingest", action="store_true", help="Disable automatic document ingestion if DB is empty")
    args = parser.parse_args()

    run_pipeline(
        topic=args.topic,
        docs_dir=args.docs_dir,
        auto_ingest=not args.no_auto_ingest
    )
