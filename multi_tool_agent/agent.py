import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
import os
from .tools.analyzer import generate_analysis_code, execute_analysis

MODEL_ID="gemini-2.5-pro"



root_agent = Agent(
    name="agent",
    model=MODEL_ID,
    description=(
        "Agent to answer questions about data."
    ),
    instruction=(
        "You are a helpful agent who can answer user questions about structured data."
    ),
    tools=[generate_analysis_code, execute_analysis],
)
