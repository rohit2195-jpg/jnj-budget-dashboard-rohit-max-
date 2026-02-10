from .analyzer import generate_analysis_code, execute_analysis
from langchain.tools import tool


@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"

@tool
def get_weather(location: str) -> str:
    """Get weather information for a location."""
    return f"Weather in {location}: Sunny, 72°F"

@tool
def generate_analysis_code_tool(user_question: str, data_path: str) -> str:
    """
    Generates Python code to analyze the dataset based on the user's question.
    """
    return generate_analysis_code(user_question, data_path)

@tool
def execute_analysis_tool(code: str) -> str:
    """
    Executes Python code and returns the output.
    """
    return execute_analysis(code)
