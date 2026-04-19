# Deployment Guide

This project runs well in local development, but deployment requires a few explicit runtime decisions.

## Runtime Topology

Two supported shapes are documented here:

### Same-Origin Deployment

Serve the frontend and backend from the same origin.

- The frontend calls `/api/*`
- No `VITE_API_BASE_URL` override is required
- CORS is simpler because requests stay same-origin

### Split-Origin Deployment

Serve the frontend and backend from different origins.

Required configuration:

- Set `VITE_API_BASE_URL` in the frontend environment
- Set `CORS_ORIGINS` on the backend to include the frontend origin

Example:

```bash
# frontend
VITE_API_BASE_URL=https://api.example.com

# backend
CORS_ORIGINS=https://app.example.com
```

## Required Environment Variables

### Backend

```bash
GEMINI_API_KEY=...
MODEL_ID=gemini-2.5-pro
```

### Optional Backend Runtime Settings

```bash
CORS_ORIGINS=https://app.example.com
FLASK_HOST=127.0.0.1
FLASK_PORT=5001
FLASK_DEBUG=false
```

### Frontend

Only required for split-origin hosting:

```bash
VITE_API_BASE_URL=https://api.example.com
```

## Node Version

The frontend toolchain expects Node `20.19.0+` or `22.12+`.

Use the pinned version in:

- [`frontend/.nvmrc`](frontend/.nvmrc)

Recommended:

```bash
cd frontend
nvm use || nvm install
```

## Frontend Build

```bash
cd frontend
nvm use || nvm install
npm install
npm run build
```

Build output is written to `frontend/dist/`.

## Backend Runtime

Local development uses:

```bash
python backend.py
```

This starts the Flask development server. That is acceptable for local work only.

For deployment:

- do not rely on the Flask dev server
- run the Flask app behind a production WSGI server
- keep `FLASK_DEBUG` disabled
- set an explicit `CORS_ORIGINS` allowlist if using split-origin hosting

## Deployment Checklist

Before calling the deployment ready:

1. Set backend env vars: `GEMINI_API_KEY`, `MODEL_ID`
2. Set `CORS_ORIGINS` if frontend and backend are on different origins
3. Set `VITE_API_BASE_URL` if using split-origin hosting
4. Build the frontend with the pinned Node version
5. Run the backend with a production WSGI setup rather than the Flask dev server
6. Verify these flows:
   - dataset listing
   - single-file upload
   - folder upload
   - analysis start
   - plan approval
   - analysis resume
   - follow-up analysis

## Files and State to Expect at Runtime

- `pre_processing/processed_data/*` will grow as datasets are cleaned and manifests are cached
- `reports/analysis_report.md` is rewritten during report generation
- `reports/followup_sessions.json` persists local follow-up session state across backend restarts

If your deployment environment uses ephemeral disk, document how you want these runtime artifacts handled before relying on session persistence.
