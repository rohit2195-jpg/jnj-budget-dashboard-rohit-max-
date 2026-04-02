# CLAUDE.md

Claude Code should use [PROJECT_GUIDE.md](/Users/rohitsattuluri/Documents/purdue/jnj-budget-dashboard-rohit-max-/PROJECT_GUIDE.md) as the shared source of truth for project context, commands, validation, architecture, and workflow.

## Agent Note

- Keep this file minimal and Claude-specific.
- Update `PROJECT_GUIDE.md` first when shared project instructions change.
- Add guidance here only when Claude-specific behavior differs from other agents.

## Key Architecture Notes

- The LangGraph pipeline in `pipeline/graph.py` has two flows through the same graph:
  - **Initial**: `entry_router → preprocess → plan → human_review → analyze → forecast → graph_gen → summarize → END`
  - **Follow-up**: `entry_router → plan → analyze → [forecast if question asks for it] → graph_gen → followup_explain → END` (skips preprocess, human_review; forecast is conditional on keyword detection)
- Routing is controlled by the `is_followup` flag in `PipelineState`. Do NOT add separate graphs for follow-ups.
- The initial pipeline flow must NOT be modified without explicit approval — it is stable and working.
- `sessions` dict in `backend.py` is in-memory (same lifetime as `MemorySaver`). Both are lost on server restart.
- Follow-up planner generates 1-2 steps (vs 3-6 for initial) to keep token costs low.
- `graphAgent/tools.py` uses a **module-level list** for the chart registry. Do NOT use `ContextVar` — LangGraph's `CompiledStateGraph` copies contextvars contexts per node, silently discarding tool mutations.
