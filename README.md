# Budget Dashboard

Budget Dashboard is a multi-agent data analysis workspace for exploring CSV and JSON datasets through natural-language prompts. A user asks a question, reviews the generated analysis plan, approves it, and receives charts, forecasts, and a markdown report in a single UI.

The repo is designed for local experimentation first, with enough structure to be reviewed or deployed after environment and hosting details are configured.

## What It Does

- Accepts uploaded or preloaded CSV/JSON datasets
- Cleans and preprocesses data before analysis
- Generates a concrete analysis plan and pauses for human approval
- Runs LLM-generated pandas analysis code against the processed data
- Produces charts, optional forecasts, and a written report
- Supports follow-up questions on the same dataset/session

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite, ApexCharts, ReactMarkdown |
| Backend | Flask, Flask-CORS |
| Orchestration | LangGraph for planning/approval pause, direct backend runner post-approval |
| LLM | Google Gemini 2.5 Pro via LangChain |
| Analysis | Pandas with LLM-generated Python |
| Forecasting | NumPy polynomial regression |

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
echo "MODEL_ID=gemini-2.5-pro" >> .env

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
- `MODEL_ID`: model identifier, currently expected to be `gemini-2.5-pro`
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

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/datasets` | List available datasets |
| POST | `/api/upload` | Upload a CSV or JSON file |
| POST | `/api/upload-folder` | Upload a folder of CSV/JSON files |
| POST | `/api/analyze/start` | Start analysis and return a plan for approval |
| POST | `/api/analyze/resume` | Continue analysis after approval |
| POST | `/api/analyze/followup` | Run a follow-up question on the same session |

### Example Requests

Start analysis:

```json
{
  "question": "Show me the top 5 cities by average price",
  "filepath": "data/USA_Housing_Dataset.csv"
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

## Generated Runtime Files

These files are created or updated at runtime and should be treated as artifacts, cache, or local session state unless you intentionally want them versioned:

- `pre_processing/processed_data/*`: cleaned datasets and manifests generated during preprocessing
- `reports/analysis_report.md`: latest generated markdown report
- `reports/followup_sessions.json`: persisted follow-up session state for local conversations

Raw user datasets live under `data/`.

## Known Limitations

- Analysis is driven by LLM-generated code, so results are not perfectly deterministic.
- Prompt wording can materially change the generated plan and resulting analysis.
- Dataset quality heavily affects output quality.
- The Flask development server is for local use only and is not a production deployment setup.
- The project currently relies on generated Python execution, so runtime safeguards improve reliability but do not make execution fully sandboxed.

## Additional Docs

- [documentation/DEPLOYMENT.md](documentation/DEPLOYMENT.md)
- [documentation/TROUBLESHOOTING.md](documentation/TROUBLESHOOTING.md)
- [documentation/ARCHITECTURE.md](documentation/ARCHITECTURE.md)
- [documentation/CONTRIBUTING.md](documentation/CONTRIBUTING.md)
- [documentation/PROJECT_GUIDE.md](documentation/PROJECT_GUIDE.md)
