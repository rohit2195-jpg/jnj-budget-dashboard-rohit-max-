from __future__ import annotations
import json
from typing import Optional, Union
from typing_extensions import TypedDict


class PipelineState(TypedDict, total=False):
    # ── inputs (set once at graph entry) ─────────────────────────────────
    question:        str            # User's natural-language question
    data_path:       str            # Path to the raw data file (first file, backward compat)
    data_paths:      Optional[list] # All raw file paths (multi-file support)

    # ── node outputs ─────────────────────────────────────────────────────
    manifest:        Optional[dict]                 # Output of callPreProcessAgent (first file, backward compat)
    manifests:       Optional[list]                 # List of per-file manifests (multi-file support)
    plan:            Optional[dict]                 # Output of create_analysis_plan {"analyses": [...]}
    analysis_output: Optional[Union[str, dict]]     # Structured JSON dict or raw stdout fallback
    forecast_output: Optional[dict]                 # Output of create_forecast {"forecasts": [...]}
    graph_data:      Optional[dict]                 # Output of create_graph {"charts": [...]}
    summary:         Optional[str]                  # Markdown report from summarize_results

    # ── follow-up support ───────────────────────────────────────────────
    is_followup:           bool                        # True when this is a follow-up question
    conversation_history:  Optional[list]               # [{question, summary_snippet}] from prior turns
    prior_charts:          Optional[list]               # Chart IDs already on the dashboard (for dedup)
    followup_explanation:  Optional[str]                # Short explanation for follow-up (replaces full summary)

    # ── control / bookkeeping ─────────────────────────────────────────────
    error:           Optional[str]  # Human-readable error, set on failure
    retry_count:     int            # Number of analyze-level retries (starts at 0)
    approved:        Optional[bool] # Human approval decision (None = not yet decided)


def get_all_data_paths(state: "PipelineState") -> list:
    """Return data_paths if set, else wrap data_path in a single-element list."""
    if state.get("data_paths"):
        return state["data_paths"]
    dp = state.get("data_path")
    if not dp:
        raise ValueError("PipelineState has neither data_paths nor data_path")
    return [dp]


def get_all_manifests(state: "PipelineState") -> list:
    """Return manifests if set, else wrap manifest in a single-element list."""
    if state.get("manifests"):
        return state["manifests"]
    if state.get("manifest"):
        return [state["manifest"]]
    return []


def serialize_analysis_output(analysis_output) -> str:
    """Serialize analysis_output to a string for downstream LLM agents."""
    if analysis_output is None:
        return ""
    if isinstance(analysis_output, dict):
        return json.dumps(analysis_output, indent=2, default=str)
    return str(analysis_output)
