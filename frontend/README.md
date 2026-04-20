# Frontend

This directory contains the React + Vite UI for Budget Dashboard.

For the full product and system documentation, start with the repo root [README.md](../README.md) and the docs index in [`documentation/`](../documentation/README.md).

## Local Commands

Use the Node version pinned in [`frontend/.nvmrc`](./.nvmrc).

```bash
nvm use || nvm install
npm install
npm run dev
npm run build
npm run lint
```

## API Configuration

The frontend calls `/api/*` relative to the current origin by default.

If the frontend and backend are served from different origins, set:

```bash
VITE_API_BASE_URL=https://api.example.com
```

## Notes

- The main UI entrypoint is `src/App.jsx`.
- Charts are rendered with ApexCharts.
- Saved conversation state is stored in browser `localStorage`.
