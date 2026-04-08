from .analyzer import generate_analysis_code, execute_analysis
from langchain.tools import tool
import json
import os



@tool
def generate_analysis_code_tool(user_question: str, data_paths_json: str) -> str:
    """
    Generates Python code to analyze the dataset based on the user's question.
    data_paths_json is a JSON string of a dict mapping short names to file paths,
    e.g. '{"sales": "pre_processing/processed_data/cleaned_sales.json"}'.
    """
    print("Agent is using the analysis code tool")
    try:
        data_paths_dict = json.loads(data_paths_json)
    except (json.JSONDecodeError, TypeError):
        # Backward compat: treat as a single path string
        stem = os.path.splitext(os.path.basename(data_paths_json))[0]
        data_paths_dict = {stem: data_paths_json}
    return generate_analysis_code(user_question, data_paths_dict=data_paths_dict)

@tool
def execute_analysis_tool(code: str, file_paths_json: str) -> str:
    """
    Executes Python code and returns the output. Used for simple data analysis.
    The generated code must define a function named 'analyze_spending_data'
    that accepts a single argument: file_paths (a dict mapping names to paths).
    file_paths_json is a JSON string of that dict.
    """
    print("Agent is executing analysis code")
    try:
        file_paths = json.loads(file_paths_json)
    except (json.JSONDecodeError, TypeError):
        # Backward compat: treat as single path
        stem = os.path.splitext(os.path.basename(file_paths_json))[0]
        file_paths = {stem: file_paths_json}

    return execute_analysis(
        code,
        file_paths,
        target_function="analyze_spending_data"
    )







