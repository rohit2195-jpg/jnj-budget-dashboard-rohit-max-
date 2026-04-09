from __future__ import annotations
import json
import math
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


class _CleanEncoder(json.JSONEncoder):
    """Round floats to 2 decimal places during JSON serialization."""
    def default(self, obj):
        return str(obj)

    def encode(self, o):
        return super().encode(self._round_floats(o))

    def _round_floats(self, obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return round(obj, 2)
        if isinstance(obj, dict):
            return {k: self._round_floats(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._round_floats(v) for v in obj]
        return obj


def serialize_analysis_output(analysis_output) -> str:
    """Serialize analysis_output to a string for downstream LLM agents."""
    if analysis_output is None:
        return ""
    if isinstance(analysis_output, dict):
        cleaned = _CleanEncoder()._round_floats(analysis_output)
        return json.dumps(cleaned, indent=2, default=str)
    return str(analysis_output)
