from __future__ import annotations
from typing import Optional
from typing_extensions import TypedDict


class PipelineState(TypedDict, total=False):
    # ── inputs (set once at graph entry) ─────────────────────────────────
    question:        str            # User's natural-language question
    data_path:       str            # Path to the raw data file

    # ── node outputs ─────────────────────────────────────────────────────
    manifest:        Optional[dict]  # Output of callPreProcessAgent
    plan:            Optional[dict]  # Output of create_analysis_plan {"analyses": [...]}
    analysis_output: Optional[str]  # Raw stdout from callAgent
    graph_data:      Optional[dict]  # Output of create_graph {"charts": [...]}
    summary:         Optional[str]  # Markdown report from summarize_results

    # ── control / bookkeeping ─────────────────────────────────────────────
    error:           Optional[str]  # Human-readable error, set on failure
    retry_count:     int            # Number of analyze-level retries (starts at 0)
    approved:        Optional[bool] # Human approval decision (None = not yet decided)
