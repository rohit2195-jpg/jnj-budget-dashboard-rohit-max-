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

Chart type mapping — choose the tool that best fits the "type" field:
- categorical → bar chart (or pie chart if ≤6 categories)
- ranking → horizontal bar chart
- timeseries → line or area chart
- comparison → stacked bar chart
- scalar → SKIP (do not create a chart for scalar types)
- scatter → scatter chart

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
            {"role": "user", "content": f"""
User Question: {user_question}

Analysis Results (structured JSON — one entry per output_label):
{analysis_output}

For each output_label in the JSON above, call the appropriate chart tool.
Skip any entries with type "scalar".
"""}
        ]
    })

    return get_graph_registry()
