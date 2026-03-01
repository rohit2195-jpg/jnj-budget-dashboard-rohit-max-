from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
import os
from dotenv import load_dotenv
from agent_tools.llm_model import model
from graphAgent.tools import (
    add_bar_chart,
    add_line_chart,
    add_pie_chart,
    add_horizontal_bar_chart,
    add_stacked_bar_chart,
    add_area_chart,
    add_scatter_chart,
    add_heatmap_chart,
    add_radar_chart,
    add_mixed_chart,
    reset_graph_registry,
    get_graph_registry
)


load_dotenv()

agent = create_agent(
    model,
    tools=[
        add_bar_chart,
        add_line_chart,
        add_pie_chart,
        add_horizontal_bar_chart,
        add_stacked_bar_chart,
        add_area_chart,
        add_scatter_chart,
        add_heatmap_chart,
        add_radar_chart,
        add_mixed_chart,
    ]
)


def create_graph(user_question, analysis_output):

    reset_graph_registry()

    system_prompt = """
You are a graph construction agent. Your input is a structured JSON object where each key is an
output_label and each value describes one analysis result.

Each result has:
- "type": categorical | timeseries | ranking | comparison | scalar | scatter
- "title": human-readable chart title
- "description": what was computed
- "unit": measurement unit (e.g. USD, count)
- For categorical/ranking: "categories" (list of labels) and "values" (list of numbers)
- For timeseries: "categories" (list of date strings) and "values" (list of numbers)
- For comparison: "categories" (list of labels) and "series" (list of {name, data} objects)
- For scatter: "data" (list of {x, y} objects)

MANDATORY CHART TYPE MAPPING (no exceptions):
- type == "categorical"  AND ≤ 6 categories  → add_pie_chart  (param: "labels", not "categories")
- type == "categorical"  AND > 6 categories  → add_bar_chart
- type == "ranking"                           → add_horizontal_bar_chart (NEVER add_bar_chart)
- type == "timeseries"                        → add_line_chart or add_area_chart
- type == "comparison"                        → add_stacked_bar_chart (pass "series" param directly)
- type == "scatter"                           → add_scatter_chart
- type == "scalar"                            → SKIP — call no tool

Rules:
- Build ONE chart per output_label (skip scalar types)
- Use the output_label as the chart_id parameter
- Use "title" as the chart title
- Map "categories"/"values"/"series"/"data" directly to tool parameters
- Do NOT output JSON, text, or markdown — ONLY call tools
"""

    agent.invoke({
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""EXAMPLE — given this input:
{{
  "Top Recipients": {{"type": "ranking", "title": "Top Recipients", "unit": "USD",
    "categories": ["Corp A", "Corp B", "Other"], "values": [724234597.25, 609128749.14, 45000000.0]}},
  "Award Trend": {{"type": "timeseries", "title": "Awards by Year", "unit": "USD",
    "categories": ["2020", "2021", "2022"], "values": [1200000.0, 1450000.0, 1600000.0]}},
  "Total Awarded": {{"type": "scalar", "title": "Total Awarded", "unit": "USD", "value": 1983363346.39}}
}}

Correct tool calls:
1. add_horizontal_bar_chart(chart_id="Top Recipients", title="Top Recipients", ...)
2. add_line_chart(chart_id="Award Trend", title="Awards by Year", ...)
3. (skip "Total Awarded" — type is scalar)

---
User Question: {user_question}

Analysis Results:
{analysis_output}

For each output_label, call the appropriate chart tool. Skip scalar types."""}
        ]
    })

    return get_graph_registry()
