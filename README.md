# Budget Dashboard

A multi-agent AI data analysis platform for exploring datasets through natural-language prompts. Ask a question about your data, approve an analysis plan, and get a visual dashboard with charts, forecasts, and a written report.

## Features

- **Natural-language queries** — ask questions about any CSV or JSON dataset
- **Multi-agent pipeline** — preprocessing, planning, analysis, forecasting, chart generation, and summarization each handled by a specialized agent
- **Human-in-the-loop** — review and approve the analysis plan before execution
- **Follow-up questions** — ask incremental follow-ups that add new charts and insights onto the existing dashboard without re-running the full pipeline
- **Interactive charts** — ApexCharts-powered visuals (bar, line, pie, scatter, heatmap, radar, stacked, forecast, and more)
- **Forecasting** — automatic timeseries detection with trend projections and confidence intervals
- **Dataset management** — upload CSV/JSON files or pick from existing datasets
- **Dark/light theme** — toggle between themes
- **Conversation history** — past analyses saved in localStorage for quick recall

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite, ApexCharts, ReactMarkdown |
| Backend | Flask, Flask-CORS |
| Orchestration | LangGraph (StateGraph + MemorySaver) |
| LLM | Google Gemini 2.5 Pro via LangChain |
| Analysis | Pandas (LLM-generated code executed via agents) |
| Forecasting | NumPy polynomial regression |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 20.19+ or 22.12+
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
npm run dev
```

The frontend runs at `http://localhost:5173` and the backend at `http://localhost:5001`.

During local development, Vite proxies `/api/*` requests to the backend on port `5001`. For a deployed frontend, set `VITE_API_BASE_URL` if the API is hosted on a different origin:

```bash
cd frontend
echo "VITE_API_BASE_URL=https://your-api-host.example.com" > .env.local
```

If the frontend and backend are served from the same origin in production, no extra frontend env var is required.

For a deployed backend, set `CORS_ORIGINS` to a comma-separated allowlist instead of relying on the local-development defaults. You can also override `FLASK_HOST`, `FLASK_PORT`, and `FLASK_DEBUG` as needed.

## How It Works

### Initial Analysis

1. User submits a question and selects a dataset
2. **Preprocess** — cleans the data and builds a schema manifest (cached by file hash)
3. **Plan** — generates 3-6 concrete pandas analysis steps
4. **Human Review** — user approves or rejects the plan
5. **Analyze** — executes the plan via LLM-generated pandas code
6. **Forecast** — detects timeseries outputs and projects future values
7. **Chart Generation** — converts results into ApexCharts configs
8. **Summarize** — produces a markdown report with cited numbers

### Follow-Up Questions

After the initial dashboard loads, a follow-up input bar appears at the bottom. Follow-ups run a lighter pipeline:

- Skips preprocessing (reuses cached manifest)
- Skips human review (auto-proceeds)
- Skips forecasting unless the question asks for it (e.g. "forecast", "predict", "trend")
- Generates 1-2 focused analysis steps instead of 3-6
- Produces a short explanation instead of a full report
- New charts append to the existing dashboard

## Project Structure

```
backend.py                  # Flask API server
pipeline/
  graph.py                  # LangGraph pipeline definition
  state.py                  # Pipeline state schema
plannerAgent/               # Analysis plan generation
agent_tools/                # Core analysis agent
forecastAgent/              # Timeseries forecasting
graphAgent/                 # Chart config generation
summarizerAgent/            # Markdown report generation
pre_processing/             # Data cleaning and manifest creation
frontend/src/
  App.jsx                   # Main React UI
  App.css                   # Styles
data/                       # Dataset files
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/datasets` | List available datasets |
| POST | `/api/upload` | Upload a CSV or JSON file |
| POST | `/api/analyze/start` | Start analysis (returns plan for approval) |
| POST | `/api/analyze/resume` | Resume after plan approval |
| POST | `/api/analyze/followup` | Run a follow-up question on the same dataset |
