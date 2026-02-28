# TODO — Project Improvement Items

Organized by priority. Each item includes the affected file(s) and a concrete fix description.

---

## High Priority

These are correctness and consistency fixes with the highest ROI.



### [H2] Pass manifest to graph_gen and summarize nodes

- **Files:** `pipeline/graph.py`, `graphAgent/graphAgent.py`, `summarizerAgent/summarizer_agent.py`
- **Problem:** Both nodes only receive raw text `analysis_output` with no schema context. Without it, chart titles are generic ("Value by Category") and summaries lack actual column names.
- **Fix:** Thread `state["manifest"]` through to both downstream nodes. Update their prompts to use column names from the manifest when generating titles and descriptions.



### [H4] Fix global state in graph_registry (thread-safety)

- **File:** `graphAgent/tools.py`
- **Problem:** `graph_registry` is a module-level list. Concurrent requests corrupt each other's chart output.
- **Fix:** Pass registry as an argument through the call stack, or use thread-local storage / Flask's `g` request context to scope it per request.

---

### [H5] Add retry on code execution failure inside agents

- **Files:** `agent_tools/analyzer.py`, `pre_processing/tools.py`
- **Problem:** If `exec()` raises an exception, the error is printed and execution continues with empty output. The pipeline never retries the LLM call to fix the broken code.
- **Fix:** Catch the exception, send the error message + failing code back to the LLM, and ask it to produce a corrected version. Limit to 2 retries.

---

## Medium Priority

Reliability improvements, developer experience, and output quality.

### [M1] Cache preprocessed data by file hash

- **Files:** `pre_processing/processing_agent.py`, `pre_processing/tools.py`
- **Problem:** The same input file is re-preprocessed from scratch on every run — slow for iterative queries on the same dataset.
- **Fix:** Compute MD5/SHA hash of the input file. If a manifest with a matching hash already exists in `pre_processing/processed_data/`, skip preprocessing and load the cached result.

---

### [M2] Parallel graph generation + summarization

- **Files:** `pipeline/graph.py`, `backend.py`
- **Problem:** `graph_gen` and `summarize` are independent (both consume `analysis_output`) but run sequentially. Running them in parallel cuts total latency ~50%.
- **Fix:** Use `concurrent.futures.ThreadPoolExecutor` or LangGraph parallel branches to run both nodes simultaneously, then merge results.

---

### [M3] Configurable API endpoint in frontend

- **File:** `frontend/src/App.jsx` (lines 74, 99, 116)
- **Problem:** `http://localhost:5001` is hardcoded; the app fails if the backend is on a different host or port.
- **Fix:** Read the base URL from `import.meta.env.VITE_API_URL` with a fallback to `http://localhost:5001`. Document the env var in `.env.example`.

---

### [M4] Don't re-preprocess on analyze failure (fix retry path)

- **File:** `pipeline/graph.py`
- **Problem:** On analyze failure, the retry route is `analyze → retry_bump → preprocess`. This re-runs preprocessing even though the manifest is still valid, wasting time and API calls.
- **Fix:** The retry edge should route back to `analyze` directly, skipping `preprocess`. Only retry preprocessing if the manifest itself is missing or invalid.

---

### [M5] Prompts reference actual column names from manifest

- **Files:** `plannerAgent/planner_agent.py`, `agent_tools/analyzer.py`
- **Problem:** Both agents receive the manifest but the prompts don't explicitly require generated code to use exact column names. LLMs sometimes invent column names that don't exist.
- **Fix:** Extract column names from the manifest and inject a `Columns available: [...]` list into the system prompt. Instruct the model that only these exact names may be used in generated code.

---

### [M6] Improve planner output validation

- **File:** `plannerAgent/planner_agent.py`
- **Problem:** The JSON parse fallback returns a single generic step. Better than crashing, but a generic step produces poor downstream output.
- **Fix:** After parsing, validate that each step references at least one column from the manifest. If validation fails, retry the LLM call once with explicit feedback about which columns to use.

---

### [M7] Add structured logging (replace print statements)

- **Files:** All agent files (`agent_tools/`, `graphAgent/`, `summarizerAgent/`, `plannerAgent/`, `pre_processing/`)
- **Problem:** All agents use bare `print()` for debugging, making it impossible to filter by severity or redirect output in production.
- **Fix:** Replace with Python `logging` module. Configure a root logger in `backend.py` with a configurable log level (`LOG_LEVEL` env var) and timestamp format.

---

### [M8] Suggested questions after preprocessing ("scout" step)

- **Files:** `pipeline/graph.py`, `plannerAgent/planner_agent.py`
- **Problem:** After preprocessing, the manifest is available, but users still have to write their question blind with no hints about what the data contains.
- **Fix:** Add an optional step after `preprocess` where the LLM generates 3–5 suggested analysis questions based on column types (dates → trend analysis, amounts → top/bottom N, etc.). Surface these in the frontend as clickable suggestions before the user types their own question.

---

### [M9] Add "Regenerate Plan" option in human review

- **Files:** `frontend/src/App.jsx`, `pipeline/graph.py`, `backend.py`
- **Problem:** The human review step only offers "Approve" — there's no way for the user to reject the plan and request a new one with different focus.
- **Fix:** Add a "Regenerate Plan" button alongside "Approve". Clicking it calls back to `/api/analyze/start` with the original question plus optional feedback text, producing a revised checklist.

---

## Low Priority / Future

Architectural upgrades and nice-to-haves for production readiness.

### [L1] LLM-as-judge quality gate before summarizer

- After `analyze`, make a cheap LLM call that scores the output on completeness and relevance (1–5 scale).
- If the score falls below a threshold, retry analysis with the critique as feedback.
- Prevents low-quality or incomplete analyses from producing misleading reports.

---

### [L2] Persistent state storage (replace MemorySaver)

- **File:** `pipeline/graph.py`
- **Problem:** `MemorySaver` is in-memory; all thread state is lost on server restart. Users cannot resume analyses after a crash or redeploy.
- **Fix:** Swap to LangGraph's `SqliteSaver` (easy) or `PostgresSaver` (production-grade). Enables resuming interrupted analyses across server restarts.

---

### [L3] Streaming responses to frontend

- **Problem:** The entire analysis completes before any response is sent to the frontend. Long analyses feel unresponsive.
- **Fix:** Use Flask streaming responses or WebSockets to emit each analysis step as it completes. Show live progress in the frontend: "Running step 2/4: Calculating top recipients…"

---

### [L4] Export analysis results (CSV / Excel / PDF)

- **Problem:** The frontend only shows charts and markdown. Users have no way to take results out of the app.
- **Fix:** Add export buttons: download raw tabular data as CSV, charts as PNG (ApexCharts has a built-in export menu), and the summary report as PDF.

---

### [L5] Authentication and multi-user support

- **Problem:** No auth — any client can call the API and read any thread's state.
- **Fix:** Add API key auth or OAuth. Scope `thread_id` generation to the authenticated user so sessions are isolated. Document setup in README.

---

### [L6] Unit and integration tests

- **Problem:** No test files exist in the project. Regressions go undetected until manual testing.
- **Fix:**
  - Backend: pytest tests for each agent with mocked LLM responses; integration test of the full pipeline using a small fixture CSV.
  - Frontend: Vitest + Testing Library for component-level tests of the approval flow and chart rendering.

---

### [L7] Code execution security hardening

- **Problem:** `exec()` runs LLM-generated code with no sandboxing. A sufficiently instructed LLM could emit code that reads secrets, deletes files, or makes network calls.
- **Fix:**
  - AST-level validation to block dangerous imports (`os.system`, `subprocess`, `shutil`, `socket`, etc.) before `exec()` is called.
  - Execution timeout via `signal.alarm` (Unix) or a `subprocess` with `timeout=` to kill runaway code.
  - Restricted `__builtins__` dict in the `exec` globals to limit available built-ins.
