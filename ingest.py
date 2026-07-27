import os
import sys
import argparse
from typing import List, Dict, Any

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from db.vector_store import get_or_create_collection, get_chroma_client


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Simple word-based chunker (~500 words per chunk, 50 word overlap)."""
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    step = chunk_size - overlap
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += step
    return chunks

def load_document(file_path: str) -> str:
    """Read text from txt, md, or pdf file."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".txt", ".md"]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except ImportError:
            print("⚠️ pypdf not installed. Skipping PDF parsing.")
            return ""
    return ""

def ingest_directory(docs_dir: str, reset: bool = False):
    """Ingest documents from directory into ChromaDB collection."""
    client = get_chroma_client()
    if reset:
        print("🧹 Resetting ChromaDB collection...")
        try:
            client.delete_collection("research_sources")
        except Exception:
            pass

    collection = get_or_create_collection(client)
    
    if not os.path.exists(docs_dir):
        print(f"⚠️ Docs directory '{docs_dir}' does not exist. Creating default directory.")
        os.makedirs(docs_dir, exist_ok=True)
        return

    files = [f for f in os.listdir(docs_dir) if os.path.isfile(os.path.join(docs_dir, f))]
    if not files:
        print(f"ℹ️ No document files found in '{docs_dir}'. Please place .txt, .md, or .pdf files there.")
        return

    documents_to_add = []
    metadatas_to_add = []
    ids_to_add = []

    doc_counter = 0
    for filename in files:
        file_path = os.path.join(docs_dir, filename)
        content = load_document(file_path)
        if not content.strip():
            continue

        doc_counter += 1
        source_id = f"SRC_{doc_counter:02d}"
        title = os.path.splitext(filename)[0].replace("_", " ").title()
        url = f"file://{os.path.abspath(file_path)}"

        chunks = chunk_text(content, chunk_size=500, overlap=50)
        print(f"📄 Processing '{filename}' -> {len(chunks)} chunks (Source ID: {source_id})")

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{source_id}_CHUNK_{idx+1}"
            documents_to_add.append(chunk)
            metadatas_to_add.append({
                "source_id": source_id,
                "title": title,
                "url": url,
                "chunk_index": idx + 1
            })
            ids_to_add.append(chunk_id)

    if documents_to_add:
        collection.upsert(
            documents=documents_to_add,
            metadatas=metadatas_to_add,
            ids=ids_to_add
        )
        print(f"✅ Ingested {len(documents_to_add)} total chunks from {doc_counter} documents into ChromaDB collection 'research_sources'.")
    else:
        print("⚠️ No valid chunks extracted for ingestion.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest source documents into ChromaDB")
    parser.add_argument("--docs_dir", type=str, default="./docs", help="Path to directory containing source documents")
    parser.add_argument("--reset", action="store_true", help="Reset ChromaDB collection before ingesting")
    args = parser.parse_args()

    ingest_directory(args.docs_dir, reset=args.reset)
