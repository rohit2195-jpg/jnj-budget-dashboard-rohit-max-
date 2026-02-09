from adk.agents import LLMAgent
from data_analysis.tools import generate_analysis_code_tool, execute_analysis_tool

# Define the agent's identity and purpose.
identity = {
    "name": "DataAnalysisAgent",
    "persona": "a data analyst that can help you analyze data",
    "mission": "to help users analyze data by generating and executing Python code",
}

# Create the LLM agent.
agent = LLMAgent(
    identity=identity,
    tools=[generate_analysis_code_tool, execute_analysis_tool],
)

