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
You are a graph construction agent.

You MUST build charts by calling the available chart tools.

Rules:
- Do NOT output JSON
- Do NOT explain
- Do NOT return markdown
- Only call tools
- Build charts that represent the analysis output
- If multiple charts are needed, call tools multiple times
"""

    agent.invoke({
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
User Question: {user_question}

Analysis Output:
{analysis_output}
"""}
        ]
    })

    return get_graph_registry()
