from __future__ import annotations

import json
import numpy as np
from langchain.tools import tool
from typing import List

forecast_registry: list = []


def reset_forecast_registry():
    global forecast_registry
    forecast_registry = []


def get_forecast_registry():
    return {"forecasts": forecast_registry}


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
Perform a linear regression forecast on time-series data and store the result.

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

    # Convert category labels to numeric indices
    x = np.arange(n, dtype=float)
    y = np.array(vals, dtype=float)

    # Fit degree-1 (linear) regression
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]

    # Residual standard deviation for confidence interval
    y_pred_hist = np.polyval(coeffs, x)
    residuals = y - y_pred_hist
    std_resid = float(np.std(residuals, ddof=1)) if n > 2 else float(np.abs(residuals).mean())
    z95 = 1.96  # 95% CI multiplier

    # R-squared
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = round(1 - ss_res / ss_tot, 4) if ss_tot > 0 else 1.0

    # Generate projected categories by extending the last label
    last_cat = cats[-1]
    try:
        last_int = int(last_cat)
        proj_cats = [str(last_int + i + 1) for i in range(forecast_periods)]
    except ValueError:
        proj_cats = [f"{last_cat}+{i + 1}" for i in range(forecast_periods)]

    # Projected values + confidence bounds
    proj_x = np.arange(n, n + forecast_periods, dtype=float)
    proj_vals = [round(float(np.polyval(coeffs, xi)), 2) for xi in proj_x]
    lower_bounds = [round(float(np.polyval(coeffs, xi) - z95 * std_resid), 2) for xi in proj_x]
    upper_bounds = [round(float(np.polyval(coeffs, xi) + z95 * std_resid), 2) for xi in proj_x]

    trend_direction = "upward" if slope > 0 else "downward" if slope < 0 else "flat"
    trend_summary = (
        f"{'Growing' if slope > 0 else 'Declining'} ~{abs(slope):,.0f} {unit}/period; "
        f"projected to reach {proj_vals[-1]:,.2f} {unit} by {proj_cats[-1]}"
    )

    result = {
        "type": "forecast",
        "forecast_id": forecast_id,
        "title": title,
        "unit": unit,
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

    forecast_registry.append(result)
    return json.dumps({"status": "ok", "forecast_id": forecast_id, "trend_direction": trend_direction})
