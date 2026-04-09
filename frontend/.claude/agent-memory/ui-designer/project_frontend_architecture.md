---
name: Frontend Architecture Overview
description: Styling approach, component structure, color system, and layout patterns used in the J&J Budget Dashboard frontend
type: project
---

Single-file React app (`frontend/src/App.jsx`) with a companion CSS file (`frontend/src/App.css`).

**Styling approach**: Custom CSS with CSS variables (no Tailwind, no Bootstrap). Light/dark mode via `[data-theme="dark"]` on `<html>`. All design tokens defined as CSS custom properties in `:root` and overridden for dark mode.

**Color palette**: Primary blue `#2563eb` (light) / sky blue `#38bdf8` (dark), accent green `#10b981` (dark only), error red `#ef4444`, success green `#16a34a`. Grays via slate scale (`--text-main`, `--text-muted`, `--border`, etc.).

**Typography**: System font stack (no explicit font import), scale uses rem units: 0.6875rem (xs) → 0.75rem → 0.8125rem → 0.875rem → 0.9375rem → 1rem → 1.125rem → 1.25rem → 1.5rem (h2 welcome).

**Layout**: Full-viewport flex column. Header (sticky, `flex-shrink: 0`) → body row (flex-grow, `overflow: hidden`) → sidebar (240px fixed) + main content (flex: 1, `overflow-y: auto`).

**Chart library**: `react-apexcharts`. Charts receive `theme: { mode }` and `chart: { background: 'transparent' }` overrides at render time for dark/light switching.

**Icon library**: `lucide-react`. Import individual icons by name.

**Header structure** (5 logical items): logo-section | search-form (flex: 1, max 560px) | dataset-picker (Database icon + select + upload-btn-group) | header-actions (theme-toggle).

**Dataset picker**: Shows files as `"name (X KB)"` and folders as `"📁 name (N files)"`. Upload buttons are grouped in `.upload-btn-group` with a visible border container. File upload uses `Upload` icon + "Files" label; folder upload uses `FolderOpen` icon + "Folder" label.

**Responsive breakpoints**:
- ≤1100px: search narrows to 420px, select narrows to 140px
- ≤1024px: sidebar hidden, dashboard-grid stacks vertically
- ≤860px: upload button labels hidden (icon-only), logo text hidden, search narrows to 280px

**Why:** Decisions made during multi-file upload UI polish (April 2026).
**How to apply:** When making further header changes, account for the 5-item flex layout and the three breakpoints that progressively collapse it.
