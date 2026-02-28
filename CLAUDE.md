# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend
```bash
python backend.py          # Start Flask API on http://localhost:5001
python main.py             # Run full pipeline via CLI (no API)
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
npm install
npm run dev                # Start Vite dev server (http://localhost:5173)
npm run build
npm run lint
```

## Validation After Code Changes

Run these after every edit to confirm nothing is broken before proceeding.

### Backend (Python syntax + import check)
```bash
# Check syntax on any modified file
python -m py_compile backend.py
python -m py_compile pipeline/graph.py
python -m py_compile agent_tools/agent.py
# etc. — replace with whichever file was changed

# Verify imports resolve (catches missing deps, bad module references)
python -c "import backend"
python -c "from pipeline.graph import build_graph"
```

### Frontend (full compile)
```bash
cd frontend && npm run build    # Compiles all JSX/JS; exits non-zero on any error
cd frontend && npm run lint     # Catches lint/style issues
```

> `python backend.py` and `npm run dev` are long-running servers — use the commands above for quick pass/fail feedback after edits. Only start the servers when you need to manually test end-to-end behavior.

## Architecture

This is a multi-agent AI data analysis platform. Users submit natural language questions about datasets; the system preprocesses data, generates a step-by-step analysis plan, pauses for human approval, then executes the plan to produce charts and a summary report.

### Pipeline (LangGraph state machine — `pipeline/graph.py`)

The core is a LangGraph graph with interrupt-based human-in-the-loop:

```
preprocess → plan → human_review [INTERRUPT] → analyze → graph_gen → summarize → END
                                                    ↓ (on failure)
                                               retry_bump → preprocess (max 2 retries)
```

- **`preprocess`** (`pre_processing/processing_agent.py`): Gemini generates pandas code to clean raw data; executes it; returns a schema manifest (columns, dtypes, row count).
- **`plan`** (`plannerAgent/planner_agent.py`): Takes user question + manifest; generates a JSON checklist of 3–6 analysis steps referencing actual column names.
- **`human_review`**: LangGraph interrupt — surfaces the checklist to the frontend for user approval before continuing.
- **`analyze`** (`agent_tools/agent.py`): LangChain agent executes each checklist step by generating and running pandas code; captures stdout.
- **`graph_gen`** (`graphAgent/graphAgent.py`): Takes raw analysis output; auto-selects from 10 chart types; generates ApexCharts-compatible configs.
- **`summarize`** (`summarizerAgent/summarizer_agent.py`): Converts analysis output into a markdown report.

### Backend API (`backend.py`)

Two endpoints drive the two-phase interaction:
- `POST /api/analyze/start` — runs `preprocess → plan → human_review (pause)`; returns the generated checklist.
- `POST /api/analyze/resume` — resumes from interrupt with user approval; runs `analyze → graph_gen → summarize`; returns charts + summary.

State is persisted across the interrupt using LangGraph's `MemorySaver` checkpointer, keyed by `thread_id`.

### Frontend (`frontend/src/App.jsx`)

Single-page React app:
1. User submits a question → calls `/api/analyze/start` → displays plan for approval.
2. User approves → calls `/api/analyze/resume` → renders charts (ApexCharts) and markdown summary.

Conversation history is stored in `localStorage` (up to 50 entries).

### Code Execution Pattern

All agents (preprocessing, analysis) generate Python code via Gemini, then execute it with `exec()` in an isolated globals dict. Functions must use specific naming patterns (e.g., `process_data`, `analyze_spending_data`) so they can be called after exec. Stdout is captured via `io.StringIO`.

## Environment Variables

Requires a `.env` file (already gitignored):
```
GEMINI_API_KEY=...
MODEL_ID=gemini-2.5-pro
```

All LLM calls use Google Gemini (`langchain-google-genai`). `ANTHROPIC_API_KEY` is in `.env` but not currently used.

## Data

- Raw datasets in `data/` (CSV and JSON)
- Preprocessed outputs written to `pre_processing/processed_data/`
- Generated reports written to `reports/`
