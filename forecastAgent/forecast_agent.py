from __future__ import annotations

import json as _json
import threading
from langchain.agents import create_agent
from dotenv import load_dotenv

from agent_tools.llm_model import model
from forecastAgent.tools import (
    forecast_timeseries,
    reset_forecast_registry,
    get_forecast_registry,
)

load_dotenv()
FORECAST_AGENT_LOCK = threading.Lock()


def _build_forecast_agent():
    return create_agent(model, tools=[forecast_timeseries])


def _has_timeseries(analysis_output_str: str) -> bool:
    """Fast pre-check: returns True only if at least one timeseries entry exists."""
    try:
        data = _json.loads(analysis_output_str)
        return any(
            isinstance(v, dict) and v.get("type") == "timeseries"
            for v in data.values()
        )
    except Exception:
        return '"timeseries"' in analysis_output_str

FORECAST_SYSTEM = """You are a forecasting agent. You receive structured JSON analysis results.

Your job:
1. Scan ALL entries in the analysis output for results with "type": "timeseries"
2. For EACH timeseries entry, call forecast_timeseries with:
   - forecast_id: the output_label (top-level key)
   - title: a descriptive forecast title (e.g. "Award Amount Forecast")
   - historical_categories: the "categories" list from the entry
   - historical_values: the "values" list from the entry
   - forecast_periods: choose 2–5 based on how many historical points exist:
       * ≤ 4 historical points → 2 periods
       * 5–8 historical points → 3 periods
       * > 8 historical points → 4–5 periods
   - unit: the "unit" field from the entry

3. Skip ALL non-timeseries types (categorical, ranking, scalar, comparison, scatter)
4. If there are NO timeseries entries, call NO tools and output ONLY: "No time-series data found."
5. Do NOT output any JSON, markdown, or explanation — ONLY call tools
"""


def create_forecast(user_question: str, analysis_output_str: str) -> dict:
    """
    Run the forecast agent over analysis output.
    Returns {"forecasts": [...]} — empty list if no timeseries data exists.
    Skips the LLM call entirely when no timeseries data is detected.
    """
    with FORECAST_AGENT_LOCK:
        reset_forecast_registry()

        # Short-circuit: avoid the LLM call when there is nothing to forecast
        if not _has_timeseries(analysis_output_str):
            return {"forecasts": []}

        try:
            agent = _build_forecast_agent()
            agent.invoke({
                "messages": [
                    {"role": "system", "content": FORECAST_SYSTEM},
                    {"role": "user", "content": f"""User question: "{user_question}"

Analysis results (JSON):
{analysis_output_str}

For each timeseries entry, call forecast_timeseries. Skip all other types."""},
                ]
            })
        except Exception as exc:
            return {"forecasts": [], "error": str(exc)}

        return get_forecast_registry()
