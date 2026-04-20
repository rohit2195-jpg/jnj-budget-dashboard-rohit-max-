# Budget Dashboard

Budget Dashboard is a multi-agent data analysis workspace for exploring CSV and JSON datasets through natural-language prompts. A user asks a question, reviews the generated analysis plan, approves it, and receives charts, forecasts, and a markdown report in a single UI.

The repo is designed for local experimentation first, with enough structure to be reviewed or deployed after environment and hosting details are configured.

## Visual Overview

![System overview](documentation/assets/system-overview.svg)

![User workflow](documentation/assets/user-workflow.svg)

## What It Does

- Accepts uploaded or preloaded CSV/JSON datasets
- Cleans and preprocesses data before analysis
- Generates a concrete analysis plan and pauses for human approval
- Runs LLM-generated pandas analysis code against the processed data
- Produces charts, optional forecasts, and a written report
- Supports follow-up questions on the same dataset/session

## Who This Is For

- Developers prototyping dataset-aware analysis experiences
- Reviewers who need a clear human approval step before analysis runs
- Teams exploring natural-language analytics on arbitrary CSV or JSON inputs
- Local operators who want a flexible analysis workspace before hardening a production deployment

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite, ApexCharts, ReactMarkdown |
| Backend | Flask, Flask-CORS |
| Orchestration | LangGraph for planning/approval pause, direct backend runner post-approval |
| LLM | Google Gemini 2.5 Pro via LangChain |
| Analysis | Pandas with LLM-generated Python |
| Forecasting | Regression-based forecasting with linear and optional quadratic models |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 20.19.0+ or 22.12+
- A Gemini API key

### Setup

```bash
# Clone and enter the repo
git clone <repo-url>
cd jnj-budget-dashboard-rohit-max-

# Python backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create .env
echo "GEMINI_API_KEY=your-key-here" > .env

# Frontend
cd frontend
nvm use || nvm install
npm install
cd ..
```

### Run

```bash
# Terminal 1 — backend
source .venv/bin/activate
export FLASK_HOST=127.0.0.1
python backend.py

# Terminal 2 — frontend
cd frontend
nvm use || nvm install
npm run dev
```

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:5001`

During local development, the frontend proxies `/api/*` requests to the backend on port `5001`.

## Environment Variables

### Backend

- `GEMINI_API_KEY`: required Gemini API key
- `MODEL_ID`: documented for future configurability, but the checked-in app is currently pinned in code to Gemini 2.5 Pro
- `CORS_ORIGINS`: comma-separated allowlist for deployed frontend origins
- `FLASK_HOST`: backend bind host, defaults to `127.0.0.1`
- `FLASK_PORT`: backend port, defaults to `5001`
- `FLASK_DEBUG`: enables Flask debug mode when set to `1`, `true`, or `yes`

### Frontend

- `VITE_API_BASE_URL`: optional API origin override for split-origin deployment

Example:

```bash
cd frontend
echo "VITE_API_BASE_URL=https://your-api-host.example.com" > .env.local
```

If frontend and backend are served from the same origin in production, `VITE_API_BASE_URL` is not required.

The frontend includes [`frontend/.nvmrc`](frontend/.nvmrc) to pin the Vite-compatible Node version used by the current toolchain. If you see a Vite engine warning on `20.18.x`, switch to `20.19.0` or newer before building for release.

## Analysis Flow

### Initial Analysis

1. The user submits a question and selects a dataset.
2. The backend preprocesses the dataset and builds a schema manifest.
3. The planner generates a 3-6 step analysis checklist.
4. The system pauses for human approval.
5. After approval, the backend runs the remaining post-plan steps directly:
   analysis, forecast generation, chart generation, and summary creation.
6. The frontend renders charts, forecasts, and the markdown report.

### Follow-Up Questions

Follow-ups reuse the cached manifest and session context:

- skip preprocessing
- skip human review
- only run forecasting if the question asks for forecast-like behavior
- append new charts to the current dashboard
- generate a shorter follow-up explanation instead of a full report

## What A Strong Prompt Looks Like

Broad prompts work best when they still communicate the kind of output you want. For example:

- `Perform a thorough analysis of this dataset and surface the strongest trends, anomalies, segments, and actionable insights.`
- `Summarize the most important relationships in this dataset, show the clearest comparisons, and call out anything unusual or high impact.`
- `Analyze this dataset end to end, identify the key drivers and outliers, and explain what a stakeholder should pay attention to first.`

If you already know what matters, add constraints such as a time grain, segment, metric, or comparison target.

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/datasets` | List available datasets |
| GET | `/api/sessions/<session_id>/dataset` | Resolve dataset metadata for a saved follow-up session |
| POST | `/api/upload` | Upload a CSV or JSON file |
| POST | `/api/upload-folder` | Upload a folder of CSV/JSON files |
| POST | `/api/analyze/start` | Start analysis and return a plan for approval |
| POST | `/api/analyze/resume` | Continue analysis after approval |
| POST | `/api/analyze/followup` | Run a follow-up question on the same session |

Runtime limits:

- uploads are limited to 250 MB per request
- accepted dataset types are `.csv` and `.json`
- folder and multi-file analyses are limited to 10 files

### Example Requests

Start analysis:

```json
{
  "question": "Show me the top 5 cities by average price",
  "filepath": "data/USA_Housing_Dataset.csv"
}
```

Start analysis with multiple files:

```json
{
  "question": "Join the order, customer, and refund files and explain the strongest revenue and retention drivers",
  "filepaths": [
    "data/upload_4930ba83/orders.csv",
    "data/upload_4930ba83/customers.csv",
    "data/upload_4930ba83/refunds.csv"
  ]
}
```

Resume after approval:

```json
{
  "thread_id": "1234-abcd",
  "approved": true
}
```

Follow-up:

```json
{
  "question": "Now compare waterfront vs non-waterfront prices over time",
  "session_id": "5678-efgh"
}
```

### Example Responses

Start analysis response:

```json
{
  "status": "pending_approval",
  "thread_id": "1234-abcd",
  "plan": {
    "analyses": [
      {
        "id": 1,
        "output_label": "Top Categories by Value",
        "description": "Group by the main category column, aggregate the primary metric, sort descending, and keep the top 15."
      }
    ]
  }
}
```

Resume response:

```json
{
  "status": "complete",
  "success": true,
  "session_id": "5678-efgh",
  "dataset_path": "data/USA_Housing_Dataset.csv",
  "dataset_name": "USA_Housing_Dataset",
  "dataset_alias": "USA Housing",
  "summary": "## Executive Summary ...",
  "graphs": {
    "charts": []
  },
  "forecast_output": {
    "forecasts": []
  }
}
```

## Example Workflow

1. Upload a dataset or choose one from `data/`
2. Ask a broad question such as:
   `Perform a thorough analysis of this dataset and highlight the strongest trends, anomalies, and actionable insights.`
3. Review the generated plan before execution
4. Approve the plan and inspect charts, forecasts, and the markdown report
5. Ask a follow-up like:
   `Now compare the major segments and explain which relationships are most important.`

Chats retain the dataset they were run against, and older saved chats may recover that identity from persisted session state when available.

Do not restart the backend after the plan is generated and before you approve it. Pending approvals are stored in LangGraph's in-memory checkpointer, so a restart invalidates the `thread_id`.

## Release Readiness Checklist

Use this as the minimum bar before pushing or publishing:

1. Run the backend and frontend with the intended local environment versions
2. Verify dataset listing, upload, plan approval, resume, and follow-up flows
3. Confirm a cached dataset path still produces correct results after a restart
4. Build the frontend with `npm run build`
5. Keep the Flask dev server out of production deployment
6. Review runtime-generated artifacts before committing
7. Confirm `.env` values and allowed frontend origins match the deployment shape

## Generated Runtime Files

These files are created or updated at runtime and should be treated as artifacts, cache, or local session state unless you intentionally want them versioned:

- `pre_processing/processed_data/*`: cleaned datasets and manifests generated during preprocessing
- `reports/analysis_report.md`: latest generated markdown report
- `reports/followup_sessions.json`: persisted follow-up session state for local conversations

That persisted session file also supports deterministic recovery of dataset identity for older saved chats.

Raw user datasets live under `data/`.

## Known Limitations

- Analysis is driven by LLM-generated code, so results are not perfectly deterministic.
- Prompt wording can materially change the generated plan and resulting analysis.
- Dataset quality heavily affects output quality.
- Forecasts are only produced for clear enough time-series patterns, and weak trends may be skipped or labeled low-confidence.
- The Flask development server is for local use only and is not a production deployment setup.
- The project currently relies on generated Python execution, so runtime safeguards improve reliability but do not make execution fully sandboxed.

## Security and Execution Model

This project executes LLM-generated Python against processed datasets. That is powerful, but it also means runtime behavior is less predictable than a fully hand-authored analysis engine.

Important implications:

- outputs can vary by prompt and dataset
- reliability guards reduce common failures but do not eliminate all unsafe or incorrect generated logic
- this repo should be treated as a controlled analysis workspace, not as a hardened multi-tenant execution platform

## Documentation Map

Start here for the project overview, then use the focused docs below:

- [documentation/README.md](documentation/README.md): index for the documentation set
- [documentation/ARCHITECTURE.md](documentation/ARCHITECTURE.md): runtime boundaries, persistence model, and execution flow
- [documentation/DEPLOYMENT.md](documentation/DEPLOYMENT.md): environment variables, hosting shape, and deployment checklist
- [documentation/TROUBLESHOOTING.md](documentation/TROUBLESHOOTING.md): known failure modes and concrete fixes
- [documentation/CONTRIBUTING.md](documentation/CONTRIBUTING.md): contribution expectations and validation workflow
- [documentation/PROJECT_GUIDE.md](documentation/PROJECT_GUIDE.md): implementation-oriented repo tour for maintainers
