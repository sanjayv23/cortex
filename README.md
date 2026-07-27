# 🤖 Multi-Agent Autonomous Research Pipeline

> An enterprise-grade, 3-agent autonomous research system powered by **LangGraph**, **Google Gemini / OpenAI**, **ChromaDB**, and a modern **FastAPI** web interface.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)
![Gemini & OpenAI](https://img.shields.io/badge/LLM-Gemini_%2F_OpenAI-green.svg)
![ChromaDB](https://img.shields.io/badge/VectorStore-ChromaDB-purple.svg)
![License](https://img.shields.io/badge/License-MIT-brightgreen.svg)

---

## 🌟 Overview

The **Multi-Agent Research Pipeline** takes any topic or research request as input and produces an in-depth, multi-section cited research report. 

It orchestrates **3 specialized AI agents** operating in a closed feedback loop:

```
                  ┌─────────────────┐
                  │   User Topic    │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ 1. RESEARCHER   │ ◄── Vector Store (ChromaDB)
                  │      Agent      │ ◄── Live Web (Wiki / DuckDuckGo)
                  └────────┬────────┘
                           │ Grounded Notes
                           ▼
                  ┌─────────────────┐
                  │   2. WRITER     │ ◄───┐
                  │     Agent       │     │ Revision Feedback
                  └────────┬────────┘     │ (Max 2 Loops)
                           │ Draft Report │
                           ▼              │
                  ┌─────────────────┐     │
                  │   3. EDITOR     │ ────┘
                  │     Agent       │
                  └────────┬────────┘
                           │ Approved Report
                           ▼
                  ┌─────────────────┐
                  │  Final Report   │
                  └─────────────────┘
```

---

## ✨ Features

- **3-Agent Feedback Architecture**:
  - 🔍 **Researcher Agent**: Decomposes complex topics into sub-questions, executes vector search against ChromaDB, triggers live Wikipedia/DuckDuckGo web fallback, and generates grounded notes with source IDs.
  - ✍️ **Writer Agent**: Drafts comprehensive Markdown reports featuring Executive Summaries, Empirical Findings per sub-question, Strategic Outlooks, and source citation tables. Performs surgical revisions based on Editor feedback.
  - 🧐 **Editor Agent**: Performs fact-checking and claim verification against original source notes. Dynamically routes drafts back for revision or approves final reports.
- **Dual LLM Provider Support with Auto-Fallback**:
  - Native support for **Google Gemini API** (`gemini-2.5-flash`, `gemini-2.0-flash`) via `google-genai`.
  - Native support for **OpenAI API** (`gpt-4o-mini`).
  - Automatic cross-provider failover if quota limits or API errors occur.
- **External Document Upload & Ingestion**:
  - Ingest `.pdf` (via `pypdf`), `.txt`, and `.md` files directly into ChromaDB vector database with text chunking (~500 words, 50 overlap).
- **Interactive Web Studio**:
  - Modern glassmorphic web dashboard (`http://localhost:8050`) with live agent state cards, detailed execution timeline accordion, grounded notes cards, and full Markdown preview.
- **CLI & REST API Ready**:
  - Full CLI runner with real-time colored log output and FastAPI backend endpoints (`/api/research`, `/api/upload_doc`, `/api/status`, `/api/reports`).

---

## 📁 Repository Structure

```
multi-agent-researcher/
├── agents/
│   ├── researcher.py       # Agent 1: Topic decomposition & note synthesis
│   ├── writer.py           # Agent 2: Report generation & surgical revision
│   └── editor.py           # Agent 3: Fact-checking & conditional routing
├── db/
│   └── vector_store.py     # ChromaDB vector store & live web fallback
├── static/                 # Web Studio Frontend
│   ├── index.html          # Single-Page Application UI
│   ├── styles.css          # Glassmorphism Dark Mode Styling
│   └── app.js              # Pipeline invocation & live timeline renderer
├── utils/
│   └── llm.py              # Dual LLM provider caller (Gemini + OpenAI)
├── docs/                   # Directory for uploaded documents
├── graph.py                # LangGraph StateGraph & conditional routing
├── state.py                # Pydantic ResearchState & schemas
├── ingest.py               # Document parsing & vector store ingestion
├── run.py                  # CLI pipeline runner
├── server.py               # FastAPI web server
├── requirements.txt        # Python dependencies
├── .env.example            # Environment configuration template
└── README.md               # Documentation
```

---

## 🚀 Quick Start

### 1. Prerequisites & Installation

Ensure Python 3.10+ is installed on your system.

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/multi-agent-researcher.git
cd multi-agent-researcher

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` to select your preferred LLM provider and add your API Key:

```env
# Choose provider: "gemini" or "openai"
LLM_PROVIDER=gemini

# Google Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# OpenAI API Configuration (Fallback/Primary)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
```

---

## 💻 Usage

### Option A: Web Studio Interface (Recommended)

Start the local web server:

```bash
python server.py
```

Open your browser and navigate to:
👉 **`http://localhost:8050`**

- Type any research topic and click **"Run Research Pipeline"**.
- Click **"Ingest Knowledge"** to upload custom `.pdf`, `.txt`, or `.md` documents.
- Inspect detailed agent execution steps, grounded notes, and final reports in real time!

---

### Option B: Command-Line Interface (CLI)

Run research directly from your terminal:

```bash
python run.py --topic "Current status of renewable energy adoption in 2026"
```

To ingest external documents before researching:

```bash
# Place your files in ./docs/ and run:
python ingest.py
python run.py --topic "Your Research Topic"
```

---

## 🛠️ API Reference

The FastAPI server exposes the following REST endpoints:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/research` | `POST` | Triggers 3-agent pipeline for a given topic JSON payload |
| `/api/upload_doc` | `POST` | Uploads and ingests `.pdf`, `.txt`, `.md` into ChromaDB |
| `/api/status` | `GET` | Returns vector store collection status and document count |
| `/api/docs` | `GET` | Lists all ingested documents in the `./docs/` directory |
| `/api/reports` | `GET` | Lists all generated reports stored in `./reports/` |

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page or submit a pull request.

---

## 📜 License

This project is licensed under the MIT License.
