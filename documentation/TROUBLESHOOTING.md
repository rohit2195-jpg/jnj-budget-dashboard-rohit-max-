# Troubleshooting

This guide covers the failure modes already observed in this repository.

## 1. `Type is not msgpack serializable: numpy.float64`

### Symptom

The backend fails during `/api/analyze/resume` with an error similar to:

```text
Type is not msgpack serializable: numpy.float64
```

### Likely Cause

Pandas or NumPy values leaked into checkpointed or persisted state.

### Fix

- Make sure you are running the current backend code
- Restart the backend fully after pulling changes
- Confirm the backend is using the direct post-approval runner instead of continuing the old checkpoint-heavy resume path

### Where To Inspect

- `backend.py`
- `pipeline/state.py`
- backend server logs during `POST /api/analyze/resume`

## 2. Vite / Node Engine Warning

### Symptom

Frontend build logs show:

```text
Vite requires Node.js version 20.19+ or 22.12+
```

### Likely Cause

You are using an older Node version, commonly `20.18.x`.

### Fix

Use the pinned Node version:

```bash
cd frontend
nvm use || nvm install
```

The repo pins the expected version in [`frontend/.nvmrc`](frontend/.nvmrc).

## 3. NumPy / pandas Import Failure In `.venv`

### Symptom

Python starts, but importing pandas or NumPy fails with an architecture or C-extension error.

### Likely Cause

The virtual environment was created with a different architecture than the Python runtime you are now using.

### Fix

- remove and recreate `.venv`
- reinstall dependencies using the intended Python runtime

Example:

```bash
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Where To Inspect

- full import traceback
- `.venv` Python path
- local machine architecture/runtime

## 4. Analysis Code Generation Fails

### Symptom

The backend reaches analysis execution but generated code errors out.

Examples already seen:

- deprecated pandas monthly offset aliases such as `'M'`
- generated code calling `.item()` on values that are already plain Python floats
- generated output that fails to emit JSON cleanly

### Fix

- retry with a more specific prompt
- inspect backend logs for the generated code block and the execution error
- confirm you are running the latest analyzer/runtime fixes

### Where To Inspect

- `agent_tools/analyzer.py`
- `agent_tools/agent.py`
- backend logs around `Agent is executing analysis code`

## 5. Analysis Output Looks Weak or Off-Target

### Symptom

The app runs, but the returned charts or summary are generic, repetitive, or not aligned with the question.

### Likely Cause

- prompt is too vague
- dataset columns are ambiguous or low quality
- cached processed output is being reused from a previous state of the data

### Fix

- use a more concrete question naming the metric and grouping you want
- verify the uploaded dataset is the intended one
- clear or inspect processed cache outputs under `pre_processing/processed_data/`

### Where To Inspect

- source dataset under `data/`
- processed dataset and manifest under `pre_processing/processed_data/`
- planner output in backend logs

## 6. Follow-Up Questions Stop Working

### Symptom

Initial analysis works, but follow-up questions fail or lose context.

### Likely Cause

- `reports/followup_sessions.json` is missing, stale, or reset
- backend restarted before expected session state was written
- local runtime artifacts were cleared

### Fix

- confirm the backend wrote `reports/followup_sessions.json`
- keep the same backend instance running for the session or verify persisted session state after restart
- rerun the initial analysis if session state is invalid

### Where To Inspect

- `reports/followup_sessions.json`
- backend logs around follow-up requests

## 7. Uploaded Dataset Does Not Appear

### Symptom

Upload succeeds or seems to succeed, but the dataset is not available for selection.

### Likely Cause

- file extension is not allowed
- upload folder contains files outside the allowed `.csv` / `.json` set
- upload did not save under the repo `data/` directory as expected

### Fix

- use only `.csv` or `.json`
- inspect the backend response from `/api/upload` or `/api/upload-folder`
- verify the new file exists under `data/`

### Where To Inspect

- `backend.py`
- `data/`
- browser network responses

## 8. Generated Reports or Cache Files Show Up in Git

### Symptom

Git status includes report files, session files, or processed artifacts.

### Likely Cause

These are runtime-generated files and may change during normal use.

### Fix

- treat them as local artifacts unless you intentionally want them versioned
- review `.gitignore`
- avoid committing them accidentally during normal development

### Common Runtime Artifacts

- `pre_processing/processed_data/*`
- `reports/analysis_report.md`
- `reports/followup_sessions.json`
