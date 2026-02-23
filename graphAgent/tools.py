from langchain.tools import tool
from typing import List

graph_registry = []

COLOR_PALETTE = [
    "#6366F1",  # Indigo
    "#22C55E",  # Green
    "#F59E0B",  # Amber
    "#EF4444",  # Red
    "#3B82F6",  # Blue
    "#A855F7",  # Purple
    "#14B8A6",  # Teal
]

def reset_graph_registry():
    global graph_registry
    graph_registry = []


def get_graph_registry():
    return {"charts": graph_registry}

@tool
def add_line_chart(
    chart_id: str,
    title: str,
    categories: List[str],
    values: List[float],
    series_name: str
):
    """
Create a line chart for showing trends over time or ordered sequences.

Use this when:
- The x-axis represents time (years, months, days)
- You want to show trends, growth, or decline
- The data has a natural order

Parameters:
- chart_id: Unique identifier for this chart
- title: Chart title
- categories: Ordered x-axis labels (e.g., years)
- values: Numeric values aligned with categories
- series_name: Label for the data series

Best for: Time series analysis, trend detection, forecasting signals.
"""
    graph_registry.append({
        "id": chart_id,
        "title": title,
        "type": "line",
        "series": [{
            "name": series_name,
            "data": values
        }],
        "options": {
            "colors": [COLOR_PALETTE[0]],
            "stroke": {
                "curve": "smooth",
                "width": 3
            },
            "markers": {
                "size": 5
            },
            "xaxis": {
                "categories": categories
            }
        }
    })
    return "Line chart added."

@tool
def add_bar_chart(
    chart_id: str,
    title: str,
    categories: List[str],
    values: List[float],
    series_name: str
):
    """
Create a vertical bar chart for comparing categories.

Use this when:
- Comparing values across distinct groups
- Ranking top/bottom categories
- Showing categorical differences

Parameters:
- chart_id: Unique identifier
- title: Chart title
- categories: Category labels (x-axis)
- values: Numeric values corresponding to each category
- series_name: Label for the series

Best for: Category comparison, rankings, top 10 lists.
"""
    graph_registry.append({
        "id": chart_id,
        "title": title,
        "type": "bar",
        "series": [{
            "name": series_name,
            "data": values
        }],
        "options": {
            "colors": COLOR_PALETTE[:len(values)],
            "plotOptions": {
                "bar": {
                    "borderRadius": 6,
                    "distributed": True  # each bar different color
                }
            },
            "xaxis": {
                "categories": categories
            }
        }
    })
    return "Bar chart added."

@tool
def add_pie_chart(
    chart_id: str,
    title: str,
    labels: List[str],
    values: List[float]
):
    """
Create a pie chart to show proportions of a whole.

Use this when:
- Showing percentage breakdowns
- Total sum represents 100%
- Limited number of categories (ideally < 8)

Parameters:
- chart_id: Unique identifier
- title: Chart title
- labels: Category names
- values: Numeric values representing portions

Best for: Market share, budget allocation, distribution analysis.
Avoid if too many categories.
"""
    graph_registry.append({
        "id": chart_id,
        "title": title,
        "type": "pie",
        "series": values,
        "options": {
            "colors": COLOR_PALETTE[:len(values)],
            "labels": labels,
            "legend": {
                "position": "bottom"
            }
        }
    })
    return "Pie chart added."

@tool
def add_horizontal_bar_chart(
    chart_id: str,
    title: str,
    categories: List[str],
    values: List[float],
    series_name: str
):
    """
Create a horizontal bar chart for category comparisons.

Use this when:
- Category labels are long
- You want easier readability
- Comparing many categories

Parameters:
- chart_id: Unique identifier
- title: Chart title
- categories: Category labels
- values: Numeric values
- series_name: Label for the series

Best for: Top 10 rankings, company comparisons, long names.
"""
    graph_registry.append({
        "id": chart_id,
        "title": title,
        "type": "bar",
        "series": [{
            "name": series_name,
            "data": values
        }],
        "options": {
            "colors": COLOR_PALETTE[:len(values)],
            "plotOptions": {
                "bar": {
                    "horizontal": True,
                    "borderRadius": 6,
                    "distributed": True
                }
            },
            "xaxis": {
                "categories": categories
            }
        }
    })
    return "Horizontal bar chart added."

@tool
def add_stacked_bar_chart(
    chart_id: str,
    title: str,
    categories: List[str],
    series: List[dict]  # [{name: str, data: [float]}]
):
    """
Create a stacked bar chart to show composition within categories.

Use this when:
- Each category contains multiple sub-groups
- You want to show both totals and breakdowns
- Comparing contribution across groups

Parameters:
- chart_id: Unique identifier
- title: Chart title
- categories: Main category labels
- series: List of series objects:
  [
    {"name": "Group A", "data": [...]},
    {"name": "Group B", "data": [...]}
  ]

Best for: Revenue breakdowns, budget segments, multi-group comparisons.
"""
    graph_registry.append({
        "id": chart_id,
        "title": title,
        "type": "bar",
        "series": series,
        "options": {
            "colors": COLOR_PALETTE,
            "plotOptions": {
                "bar": {
                    "horizontal": False
                }
            },
            "chart": {
                "stacked": True
            },
            "xaxis": {
                "categories": categories
            }
        }
    })
    return "Stacked bar chart added."


@tool
def add_area_chart(
    chart_id: str,
    title: str,
    categories: List[str],
    values: List[float],
    series_name: str
):
    """
Create an area chart to emphasize magnitude over time.

Use this when:
- Showing trends like a line chart
- You want stronger visual emphasis on volume
- Demonstrating cumulative growth

Parameters:
- chart_id: Unique identifier
- title: Chart title
- categories: Ordered labels (usually time-based)
- values: Numeric values
- series_name: Series label

Best for: Growth trends, cumulative values, volume over time.
"""
    graph_registry.append({
        "id": chart_id,
        "title": title,
        "type": "area",
        "series": [{
            "name": series_name,
            "data": values
        }],
        "options": {
            "colors": [COLOR_PALETTE[1]],
            "stroke": {
                "curve": "smooth"
            },
            "fill": {
                "type": "gradient"
            },
            "xaxis": {
                "categories": categories
            }
        }
    })
    return "Area chart added."



@tool
def add_scatter_chart(
    chart_id: str,
    title: str,
    data: List[List[float]],  # [[x, y], [x, y]]
    series_name: str
):
    """
Create a scatter plot to analyze correlation between two numeric variables.

Use this when:
- Comparing two continuous variables
- Looking for correlation patterns
- Detecting clusters or outliers

Parameters:
- chart_id: Unique identifier
- title: Chart title
- data: List of [x, y] numeric pairs
- series_name: Label for the dataset

Best for: Correlation analysis, regression exploration, anomaly detection.
"""
    graph_registry.append({
        "id": chart_id,
        "title": title,
        "type": "scatter",
        "series": [{
            "name": series_name,
            "data": data
        }],
        "options": {
            "colors": [COLOR_PALETTE[2]],
            "xaxis": {
                "type": "numeric"
            }
        }
    })
    return "Scatter chart added."


@tool
def add_heatmap_chart(
    chart_id: str,
    title: str,
    series: List[dict]  # [{ name: str, data: [{x: str, y: float}] }]
):
    """
Create a heatmap to visualize intensity across a matrix.

Use this when:
- Comparing two categorical dimensions
- Showing density or intensity
- Highlighting high/low concentration areas

Parameters:
- chart_id: Unique identifier
- title: Chart title
- series: List structured as:
  [
    {
      "name": "Row Category",
      "data": [{"x": "Column A", "y": 10}, ...]
    }
  ]

Best for: Activity frequency, performance matrices, time vs category analysis.
"""
    graph_registry.append({
        "id": chart_id,
        "title": title,
        "type": "heatmap",
        "series": series,
        "options": {
            "colors": ["#008FFB"],
            "dataLabels": {
                "enabled": False
            }
        }
    })
    return "Heatmap chart added."


@tool
def add_radar_chart(
    chart_id: str,
    title: str,
    categories: List[str],
    values: List[float],
    series_name: str
):
    """
Create a radar chart to compare multiple metrics for a single entity.

Use this when:
- Comparing multiple dimensions
- Evaluating performance across criteria
- Showing strengths vs weaknesses

Parameters:
- chart_id: Unique identifier
- title: Chart title
- categories: Metric names
- values: Numeric values for each metric
- series_name: Label for the entity

Best for: Performance evaluation, skill comparison, multi-metric scoring.
"""
    graph_registry.append({
        "id": chart_id,
        "title": title,
        "type": "radar",
        "series": [{
            "name": series_name,
            "data": values
        }],
        "options": {
            "colors": [COLOR_PALETTE[4]],
            "xaxis": {
                "categories": categories
            }
        }
    })
    return "Radar chart added."


@tool
def add_mixed_chart(
    chart_id: str,
    title: str,
    categories: List[str],
    bar_values: List[float],
    line_values: List[float],
    bar_series_name: str,
    line_series_name: str
):
    """
Create a mixed chart combining bar and line series.

Use this when:
- Comparing two related metrics
- Showing volume (bars) and trend (line)
- Dual-metric analysis

Parameters:
- chart_id: Unique identifier
- title: Chart title
- categories: Shared x-axis labels
- bar_values: Numeric values for bar series
- line_values: Numeric values for line series
- bar_series_name: Label for bar data
- line_series_name: Label for line data

Best for: Revenue vs growth rate, volume vs percentage, dual-axis insights.
"""
    graph_registry.append({
        "id": chart_id,
        "title": title,
        "series": [
            {
                "name": bar_series_name,
                "type": "column",
                "data": bar_values
            },
            {
                "name": line_series_name,
                "type": "line",
                "data": line_values
            }
        ],
        "options": {
            "colors": [COLOR_PALETTE[0], COLOR_PALETTE[3]],
            "xaxis": {
                "categories": categories
            }
        }
    })
    return "Mixed chart added."