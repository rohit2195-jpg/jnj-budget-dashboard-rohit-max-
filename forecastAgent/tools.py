from __future__ import annotations

from contextvars import ContextVar
import json
import numpy as np
from langchain.tools import tool
from typing import List

forecast_registry_var: ContextVar[list] = ContextVar("forecast_registry", default=[])


def reset_forecast_registry():
    forecast_registry_var.set([])


def get_forecast_registry():
    return {"forecasts": list(forecast_registry_var.get())}


def _append_forecast(result: dict):
    forecasts = list(forecast_registry_var.get())
    forecasts.append(result)
    forecast_registry_var.set(forecasts)


def _adjusted_r2(r2, n, k):
    """Adjusted R² to penalise model complexity."""
    if n - k - 1 <= 0:
        return r2
    return 1 - (1 - r2) * (n - 1) / (n - k - 1)


def _is_currency_unit(unit):
    return unit.upper() in ("USD", "DOLLARS", "DOLLAR", "$", "US DOLLARS")


def _fmt_value(val, unit):
    """Format a numeric value with optional currency prefix."""
    if _is_currency_unit(unit):
        return f"${val:,.0f}"
    return f"{val:,.0f} {unit}"


def _confidence_label(r2):
    if r2 >= 0.9:
        return "high"
    if r2 >= 0.7:
        return "moderate"
    return "low"


@tool
def forecast_timeseries(
    forecast_id: str,
    title: str,
    historical_categories: List[str],
    historical_values: List[float],
    forecast_periods: int,
    unit: str,
) -> str:
    """
Perform a regression forecast on time-series data and store the result.

Use this tool when:
- The analysis output contains a result with type == "timeseries"
- You want to project future values beyond the last historical point

Parameters:
- forecast_id: Unique identifier (use the output_label from analysis)
- title: Human-readable forecast title
- historical_categories: Ordered x-axis labels (e.g. ["2020","2021","2022"])
- historical_values: Numeric values aligned with historical_categories
- forecast_periods: How many future periods to project (typically 2–5)
- unit: Measurement unit (e.g. "USD", "count")

Returns a JSON summary string after storing the forecast result.
"""
    cats = list(historical_categories)
    vals = list(historical_values)
    n = len(vals)

    if n < 2:
        return json.dumps({"error": "Need at least 2 historical points to forecast."})

    x = np.arange(n, dtype=float)
    y = np.array(vals, dtype=float)

    # ── Model selection: linear vs quadratic ────────────────────────────────
    # Always fit linear
    coeffs_lin = np.polyfit(x, y, 1)
    y_pred_lin = np.polyval(coeffs_lin, x)
    ss_res_lin = float(np.sum((y - y_pred_lin) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2_lin = 1 - ss_res_lin / ss_tot if ss_tot > 0 else 1.0
    adj_r2_lin = _adjusted_r2(r2_lin, n, 1)

    # Try quadratic if we have enough points
    use_quadratic = False
    if n >= 4:
        coeffs_quad = np.polyfit(x, y, 2)
        y_pred_quad = np.polyval(coeffs_quad, x)
        ss_res_quad = float(np.sum((y - y_pred_quad) ** 2))
        r2_quad = 1 - ss_res_quad / ss_tot if ss_tot > 0 else 1.0
        adj_r2_quad = _adjusted_r2(r2_quad, n, 2)
        # Only use quadratic if it improves adjusted R² by at least 0.05
        if adj_r2_quad - adj_r2_lin >= 0.05:
            use_quadratic = True

    if use_quadratic:
        coeffs = coeffs_quad
        r_squared = round(r2_quad, 4)
        model_type = "quadratic"
        std_resid = float(np.std(y - y_pred_quad, ddof=3)) if n > 3 else float(np.abs(y - y_pred_quad).mean())
    else:
        coeffs = coeffs_lin
        r_squared = round(r2_lin, 4)
        model_type = "linear"
        std_resid = float(np.std(y - y_pred_lin, ddof=2)) if n > 2 else float(np.abs(y - y_pred_lin).mean())

    slope = coeffs_lin[0]  # use linear slope for trend direction

    # ── R² threshold: skip if too low ───────────────────────────────────────
    if r_squared < 0.3:
        return json.dumps({
            "status": "skipped",
            "forecast_id": forecast_id,
            "reason": f"R² = {r_squared:.2f} — the data does not follow a clear trend, so a forecast would be unreliable.",
        })

    low_confidence_warning = None
    if r_squared < 0.5:
        low_confidence_warning = (
            "This forecast has low model confidence. The data does not closely follow "
            "the fitted trend, so projections should be treated with caution."
        )

    # ── Generate projected categories ───────────────────────────────────────
    last_cat = cats[-1]
    try:
        last_int = int(last_cat)
        proj_cats = [str(last_int + i + 1) for i in range(forecast_periods)]
    except ValueError:
        proj_cats = [f"{last_cat}+{i + 1}" for i in range(forecast_periods)]

    # ── Projected values + proper prediction intervals ──────────────────────
    proj_x = np.arange(n, n + forecast_periods, dtype=float)
    x_mean = np.mean(x)
    ss_x = float(np.sum((x - x_mean) ** 2))

    proj_vals = []
    lower_bounds = []
    upper_bounds = []
    for xi in proj_x:
        predicted = float(np.polyval(coeffs, xi))
        # Prediction interval that widens with extrapolation distance
        se_pred = std_resid * np.sqrt(1 + 1 / n + (xi - x_mean) ** 2 / ss_x) if ss_x > 0 else std_resid
        proj_vals.append(round(predicted, 2))
        lower_bounds.append(round(predicted - 1.96 * se_pred, 2))
        upper_bounds.append(round(predicted + 1.96 * se_pred, 2))

    # ── Trend direction & human-readable summary ────────────────────────────
    trend_direction = "upward" if slope > 0 else "downward" if slope < 0 else "flat"
    conf_label = _confidence_label(r_squared)

    last_proj = proj_vals[-1]
    last_lo = lower_bounds[-1]
    last_hi = upper_bounds[-1]
    last_period = proj_cats[-1]

    trend_verb = "growing" if slope > 0 else "declining"
    trend_summary = (
        f"Values are {trend_verb} by approximately {_fmt_value(abs(slope), unit)} per period "
        f"({model_type} model). By {last_period}, we project a value of "
        f"{_fmt_value(last_proj, unit)} (95% CI: {_fmt_value(last_lo, unit)} \u2013 "
        f"{_fmt_value(last_hi, unit)}). "
        f"Model confidence is {conf_label} (R\u00b2 = {r_squared:.2f})."
    )

    result = {
        "type": "forecast",
        "forecast_id": forecast_id,
        "title": title,
        "unit": unit,
        "model_type": model_type,
        "historical": {
            "categories": cats,
            "values": vals,
        },
        "projected": {
            "categories": proj_cats,
            "values": proj_vals,
            "lower_bound": lower_bounds,
            "upper_bound": upper_bounds,
        },
        "r_squared": r_squared,
        "trend_direction": trend_direction,
        "trend_summary": trend_summary,
    }

    if low_confidence_warning:
        result["low_confidence_warning"] = low_confidence_warning

    _append_forecast(result)
    return json.dumps({"status": "ok", "forecast_id": forecast_id, "trend_direction": trend_direction})
