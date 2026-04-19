# Contributing

This guide is intentionally short. It focuses on the repo-specific practices needed to avoid breaking runtime behavior.

## Local Setup

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
nvm use || nvm install
npm install
```

The frontend toolchain expects the Node version pinned in [`frontend/.nvmrc`](frontend/.nvmrc).

## Validation Before Pushing

Run the checks that match your changes.

### Python

```bash
python3 -m py_compile backend.py main.py $(rg --files -g '*.py' agent_tools forecastAgent plannerAgent pre_processing summarizerAgent pipeline graphAgent)
```

### Frontend

```bash
cd frontend
npm run lint
npm run build
```

## Generated and Runtime Files

This repo produces runtime artifacts during normal use.

Examples:

- `pre_processing/processed_data/*`
- `reports/analysis_report.md`
- `reports/followup_sessions.json`

Do not commit these by default unless the change intentionally updates a checked-in example, fixture, or canonical artifact.

## Repo Hygiene

- Avoid committing local session state or generated reports accidentally.
- Be careful around dynamic execution contracts in preprocessing and analysis agents.
- Prefer behavior-preserving changes unless the task explicitly changes runtime flow.
- When changing public runtime behavior or environment expectations, update docs in the same change.

## Documentation Update Rules

- User-visible setup/runtime/config changes should update `README.md` or `DEPLOYMENT.md`
- Failure-mode and environment issue changes should update `TROUBLESHOOTING.md`
- Architecture or execution-flow changes should update `ARCHITECTURE.md`
- Repo workflow changes should update this file

## Tracked Cache / Bytecode Cleanup

If tracked `__pycache__` or `.pyc` files still exist in repo history, clean them deliberately in a focused hygiene commit rather than mixing that cleanup into unrelated feature work.
