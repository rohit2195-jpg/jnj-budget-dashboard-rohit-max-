from adk.tools import tool
from data_analysis.analyzer import generate_analysis_code, execute_analysis

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
