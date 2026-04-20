from __future__ import annotations
import json
import math
from datetime import date, datetime
from typing import Optional, Union
from typing_extensions import TypedDict

try:
    import numpy as _np
except Exception:  # pragma: no cover - numpy is installed here, but keep this defensive
    _np = None

try:
    import pandas as _pd
except Exception:  # pragma: no cover
    _pd = None


class PipelineState(TypedDict, total=False):
    # ── inputs (set once at graph entry) ─────────────────────────────────
    question:        str            # User's natural-language question
    data_path:       str            # Path to the raw data file (first file, backward compat)
    data_paths:      Optional[list] # All raw file paths (multi-file support)
    dataset_path:    Optional[str]  # Canonical dataset path selected in the UI
    dataset_name:    Optional[str]  # Human display name for the dataset
    dataset_alias:   Optional[str]  # AI/friendly alias reused per dataset

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


def sanitize_for_state(value):
    """
    Recursively convert pandas/numpy values into JSON/msgpack-safe Python types.

    LangGraph checkpoints can fail if any node returns numpy scalars, pandas NA,
    timestamps, periods, timedeltas, NaN, or infinities. This function normalizes
    those values at the graph boundary instead of trusting LLM-generated code.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if _np is not None and isinstance(value, _np.generic):
        return sanitize_for_state(value.item())
    if _np is not None and isinstance(value, _np.ndarray):
        return [sanitize_for_state(item) for item in value.tolist()]

    if _pd is not None:
        if value is _pd.NA:
            return None
        if isinstance(value, (_pd.Timestamp, _pd.Timedelta, _pd.Period)):
            return str(value)
        if isinstance(value, _pd.Series):
            return [sanitize_for_state(item) for item in value.tolist()]
        if isinstance(value, _pd.Index):
            return [sanitize_for_state(item) for item in value.tolist()]
        if isinstance(value, _pd.DataFrame):
            return [
                {str(key): sanitize_for_state(val) for key, val in row.items()}
                for row in value.to_dict(orient="records")
            ]

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            str(key): sanitize_for_state(val)
            for key, val in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [sanitize_for_state(item) for item in value]

    return value


def serialize_analysis_output(analysis_output) -> str:
    """Serialize analysis_output to a string for downstream LLM agents."""
    if analysis_output is None:
        return ""
    if isinstance(analysis_output, dict):
        cleaned = _CleanEncoder()._round_floats(sanitize_for_state(analysis_output))
        return json.dumps(cleaned, indent=2, default=str)
    return str(analysis_output)
