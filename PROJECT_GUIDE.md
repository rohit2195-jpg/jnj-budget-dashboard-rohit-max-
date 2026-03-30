# PROJECT_GUIDE.md

Canonical project guide for AI coding agents and humans working in this repository.

## Project Overview

This repo is a multi-agent AI data analysis platform for exploring datasets through natural-language prompts.

- Backend: Flask API in `backend.py`
- Frontend: React + Vite app in `frontend/`
- Orchestration: LangGraph pipeline in `pipeline/graph.py`
- LLM provider: Google Gemini via `langchain-google-genai`

Users submit a question about a dataset. The system preprocesses the data, generates an analysis plan, pauses for human approval, then resumes to run analysis, forecasting, chart generation, and summarization.

## Main Commands

### Backend
```bash
source .venv/bin/activate
.venv/bin/pip install -r requirements.txt
.venv/bin/python backend.py
.venv/bin/python main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
npm run build
npm run lint
```

## Validation After Changes

Prefer quick pass/fail checks over long-running servers.

### Python
Always use the repo venv Python because dependencies are already installed there.

```bash
.venv/bin/python -m py_compile backend.py
.venv/bin/python -m py_compile pipeline/graph.py
.venv/bin/python -m py_compile agent_tools/agent.py
.venv/bin/python -c "import backend"
.venv/bin/python -c "from pipeline.graph import build_graph"
```

Replace file paths with the specific Python files you changed.

### Frontend
```bash
cd frontend && npm run build
cd frontend && npm run lint
```

## Architecture

### LangGraph Pipeline

Core pipeline in `pipeline/graph.py`:

`preprocess -> plan -> human_review [interrupt] -> analyze -> forecast -> graph_gen -> summarize -> END`

Failure path:

`retry_bump -> preprocess` with a maximum of 2 retries.

### Pipeline Stages

- `preprocess` in `pre_processing/processing_agent.py`
  - Gemini generates pandas cleanup code.
  - Processed outputs are cached by file hash.
  - Returns a schema manifest with columns, dtypes, and row count.
- `plan` in `plannerAgent/planner_agent.py`
  - Produces a 3 to 6 step JSON analysis checklist based on the user prompt and manifest.
- `human_review`
  - LangGraph interrupt surfaced to the frontend for approval.
- `analyze` in `agent_tools/agent.py`
  - Executes checklist steps by generating and running pandas code.
- `forecast` in `forecastAgent/forecast_agent.py`
  - Detects timeseries outputs and projects future values with confidence intervals and R-squared metrics.
  - Non-fatal if forecasting fails.
- `graph_gen` in `graphAgent/graphAgent.py`
  - Converts analysis outputs into ApexCharts-compatible chart configs.
- `summarize` in `summarizerAgent/summarizer_agent.py`
  - Produces the markdown report shown in the UI.

### Forecasting

Forecast logic lives in `forecastAgent/`.

- `forecast_agent.py` coordinates forecasting
- `tools.py` performs NumPy-based linear regression

Forecasts include:

- historical values
- projected values
- lower and upper confidence bounds
- R-squared
- trend direction
- human-readable trend summary

### Charting

Chart generation lives in `graphAgent/tools.py`.

Supported chart types:

- `line`
- `bar`
- `pie`
- `horizontal_bar`
- `stacked_bar`
- `area`
- `scatter`
- `heatmap`
- `radar`
- `mixed`
- `forecast`

### Backend API

`backend.py` exposes the two-step flow:

- `POST /api/analyze/start`
  - Runs `preprocess -> plan -> human_review`
  - Returns the generated checklist for approval
- `POST /api/analyze/resume`
  - Resumes after approval
  - Runs `analyze -> forecast -> graph_gen -> summarize`
  - Returns `status`, `summary`, `graphs`, and `forecast_output`

Pipeline state across the approval pause is persisted with LangGraph `MemorySaver`, keyed by `thread_id`.

### Frontend

Primary UI file: `frontend/src/App.jsx`

The frontend:

- submits the initial question
- displays the generated plan for approval
- resumes analysis after approval
- renders charts with ApexCharts
- renders a Future Outlook section for forecasts
- stores conversation history in `localStorage`

## Code Execution Pattern

Several agents generate Python code with Gemini and execute it via `exec()` inside isolated globals.

Be careful when editing code that depends on generated function names or dynamic execution contracts. The generated code must remain compatible with expected entrypoint names such as `process_data`.

## Environment

Expected `.env` values:

```bash
GEMINI_API_KEY=...
MODEL_ID=gemini-2.5-pro
```

`ANTHROPIC_API_KEY` may exist in `.env` but is not part of the active pipeline.

## Data and Outputs

- Raw datasets: `data/`
- Processed artifacts: `pre_processing/processed_data/`
- Generated reports: `reports/`

## Working Rules

- Avoid deleting or overwriting generated datasets and reports unless the task requires it.
- When changing Python pipeline logic, validate with `py_compile` and a minimal import check.
- When changing frontend behavior, run both `npm run build` and `npm run lint` in `frontend/`.
- Keep agent-specific instruction files small and point them here for shared project context.
