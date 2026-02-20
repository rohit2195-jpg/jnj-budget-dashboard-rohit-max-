from .analyzer import generate_analysis_code, execute_analysis
from langchain.tools import tool
import json
import os



@tool
def generate_analysis_code_tool(user_question: str, data_path: str) -> str:
    """
    Generates Python code to analyze the dataset based on the user's question.
    """
    print("Agent is using the analysis code tool")
    return generate_analysis_code(user_question, data_path)

@tool
def execute_analysis_tool(code: str, filepath: str) -> str:
    """
    Executes Python code and returns the output. Used for simple data analysis.
    The generated code must define a function named 'analyze_spending_data'
    that accepts a single argument: file_path.
    """
    print("Agent is executing analysis code")

    return execute_analysis(
        code,
        filepath,
        target_function="analyze_spending_data"
    )







