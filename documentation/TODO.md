# TODO — Project Improvement Items

Organized by priority. Each item includes the affected file(s) and a concrete fix description.

---

## High Priority

### [H1] Pass manifest to graph_gen and summarize nodes

- **Files:** `pipeline/graph.py`, `graphAgent/graphAgent.py`, `summarizerAgent/summarizer_agent.py`
- **Problem:** Both nodes only receive raw text `analysis_output` with no schema context. Without it, chart titles are generic ("Value by Category") and summaries lack actual column names.
- **Fix:** Thread `state["manifest"]` through to both downstream nodes. Update their prompts to use column names from the manifest when generating titles and descriptions.

---

### [H2] Add retry on code execution failure inside agents

- **Files:** `agent_tools/analyzer.py`, `pre_processing/tools.py`
- **Problem:** If `exec()` raises an exception, the error is printed and execution continues with empty output. The pipeline never retries the LLM call to fix the broken code.
- **Fix:** Catch the exception, send the error message + failing code back to the LLM, and ask it to produce a corrected version. Limit to 2 retries.

---

## Medium Priority

### [M1] Configurable API endpoint in frontend

- **File:** `frontend/src/App.jsx`
- **Problem:** `http://localhost:5001` is hardcoded in multiple places; the app fails if the backend is on a different host or port.
- **Fix:** Read the base URL from `import.meta.env.VITE_API_URL` with a fallback to `http://localhost:5001`. Document the env var in `.env.example`.

---

### [M2] Don't re-preprocess on analyze failure (fix retry path)

- **File:** `pipeline/graph.py`
- **Problem:** On analyze failure, the retry route is `analyze → retry_bump → preprocess`. This re-runs preprocessing even though the manifest is still valid, wasting time and API calls.
- **Fix:** The retry edge should route back to `analyze` directly, skipping `preprocess`. Only retry preprocessing if the manifest itself is missing or invalid.

---

### [M3] Improve planner output validation

- **File:** `plannerAgent/planner_agent.py`
- **Problem:** The JSON parse fallback returns a single generic step. A generic step produces poor downstream output.
- **Fix:** After parsing, validate that each step references at least one column from the manifest. If validation fails, retry the LLM call once with explicit feedback about which columns to use.

---

### [M4] Add structured logging (replace print statements)

- **Files:** All agent files (`agent_tools/`, `graphAgent/`, `summarizerAgent/`, `plannerAgent/`, `pre_processing/`)
- **Problem:** All agents use bare `print()` for debugging, making it impossible to filter by severity or redirect output in production.
- **Fix:** Replace with Python `logging` module. Configure a root logger in `backend.py` with a configurable log level (`LOG_LEVEL` env var) and timestamp format.

---

### [M5] Persist follow-up sessions across server restarts

- **Files:** `backend.py`, `pipeline/graph.py`
- **Problem:** The `sessions` dict and `MemorySaver` are both in-memory. Server restarts lose all session state, breaking follow-up questions for any active conversation.
- **Fix:** Move session data to SQLite or Redis. Consider swapping `MemorySaver` to `SqliteSaver` at the same time.

---

### [M6] Add "Regenerate Plan" option in human review

- **Files:** `frontend/src/App.jsx`, `pipeline/graph.py`, `backend.py`
- **Problem:** The human review step only offers "Approve" or "Reject" — there's no way to request a revised plan with different focus.
- **Fix:** Add a "Regenerate Plan" button. Clicking it calls back to `/api/analyze/start` with the original question plus optional feedback text, producing a revised checklist.

---

## Low Priority / Future

### [L1] Streaming responses to frontend

- **Problem:** The entire analysis completes before any response is sent. Long analyses feel unresponsive.
- **Fix:** Use Flask streaming responses or WebSockets to emit each analysis step as it completes. Show live progress: "Running step 2/4: Calculating top recipients..."

---

### [L2] Export analysis results (CSV / Excel / PDF)

- **Problem:** Users have no way to take results out of the app.
- **Fix:** Add export buttons: download raw tabular data as CSV, charts as PNG (ApexCharts built-in export), and the summary report as PDF.

---

### [L3] Authentication and multi-user support

- **Problem:** No auth — any client can call the API and read any thread's state.
- **Fix:** Add API key auth or OAuth. Scope `thread_id` and `session_id` to the authenticated user so sessions are isolated.

---

### [L4] Unit and integration tests

- **Problem:** No test files exist. Regressions go undetected until manual testing.
- **Fix:**
  - Backend: pytest tests for each agent with mocked LLM responses; integration test of the full pipeline using a small fixture CSV.
  - Frontend: Vitest + Testing Library for component-level tests of the approval flow, chart rendering, and follow-up flow.

---

### [L5] Code execution security hardening

- **Problem:** `exec()` runs LLM-generated code with no sandboxing.
- **Fix:**
  - AST-level validation to block dangerous imports (`os.system`, `subprocess`, `shutil`, `socket`, etc.) before `exec()`.
  - Execution timeout via `signal.alarm` (Unix) or subprocess with `timeout=`.
  - Restricted `__builtins__` dict in the `exec` globals.

---

### [L6] LLM-as-judge quality gate before summarizer

- After `analyze`, make a cheap LLM call that scores the output on completeness and relevance (1-5 scale).
- If the score falls below a threshold, retry analysis with the critique as feedback.
