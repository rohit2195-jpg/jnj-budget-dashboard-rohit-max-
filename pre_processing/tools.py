
import os
from pathlib import Path
import pandas as pd
from google import genai
from dotenv import load_dotenv
from agent_tools.llm_model import model
from langchain.tools import tool
import json


def _compute_output_path(data_path: str) -> str:
    """Deterministically compute the cleaned output path from the input path."""
    safe_stem = Path(data_path).stem.replace(" ", "_")
    return f"pre_processing/processed_data/cleaned_{safe_stem}.json"


@tool
def generate_analysis_code(data_path: str) -> str:
    """
    Generates Python code to pre-process the dataset.
    The output path is determined by the input filename — no LLM involvement in naming.
    """
    print("Pre-processing generating cleaning code")
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return "print('Error: GEMINI_API_KEY not found. Please set it in a .env file.')"

    if not os.path.exists(data_path):
        print(f'Error: Data file not found at {data_path}')
        return

    # Deterministic output path — same formula used in callPreProcessAgent
    output_path = _compute_output_path(data_path)

    try:
        if data_path.lower().endswith('.csv'):
            df = pd.read_csv(data_path)
        else:
            df = pd.read_json(data_path)
        df_header = df.columns.tolist()
        df_first_rows = df.head(5).to_string()
    except Exception as e:
        print(f'Error reading data file: {e}')
        return

    prompt = f"""
    You are a data pre-processor.
    The dataset is located at: {data_path}
    The data columns are: {df_header}
    First five rows: {df_first_rows}

    Please pre-process the data by cleaning, transforming, and organizing raw data into a usable format for future analysis and machine learning.
    Hardcode both the input and output paths in your code.

    Generate a Python script that uses pandas and:
    1. Loads the data from '{data_path}'
       - Use pd.read_csv if the path ends with .csv, otherwise use pd.read_json
    2. Cleans and pre-processes the data (handle nulls, fix types, rename columns if needed)
    3. Saves the cleaned dataset as JSON to EXACTLY this path: '{output_path}'
       - Include: os.makedirs('pre_processing/processed_data', exist_ok=True) before saving
    4. Prints a brief summary of the cleaned dataset (shape, columns, sample rows)

    The function must be named 'process_data' and accept a single argument: file_path (the input data path).
    The output path must be hardcoded inside the function as: '{output_path}'
    Your code should be executable and self-contained. Do not include any markdown formatting.
    """

    try:
        response = model.invoke(prompt)
        response = response.text
        response = response.strip('```').lstrip('python')
        print('------Code generated------')
        print(response)
        return response
    except Exception as e:
        print(f'An error occurred with the LLM: {e}')
        return

def execute_analysis(code, *args, target_function=None, **kwargs):
    """
    Executes Python code and returns the output. Used for simple data analysis.
    The generated code must define a function named 'analyze_spending_data'
    """
    from io import StringIO
    import sys
    import inspect

    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    exec_globals = {"__name__": "__main__"}

    try:
        # Execute generated code
        exec(code, exec_globals)

        # Collect functions
        functions = {
            name: obj
            for name, obj in exec_globals.items()
            if callable(obj) and inspect.isfunction(obj)
        }

        if not functions:
            print("No functions found in generated code.")
            return captured_output.getvalue()

        # Select target function
        if target_function:
            if target_function not in functions:
                print(f"Function '{target_function}' not found.")
                return captured_output.getvalue()
            target_fn = functions[target_function]
        else:
            if len(functions) != 1:
                print(
                    "Multiple functions found. "
                    "Specify target_function explicitly."
                )
                return captured_output.getvalue()
            target_fn = next(iter(functions.values()))

        # Validate required arguments
        sig = inspect.signature(target_fn)
        try:
            sig.bind(*args, **kwargs)
        except TypeError as bind_error:
            print(f"Argument mismatch: {bind_error}")
            return captured_output.getvalue()

        # Call function
        target_fn(*args, **kwargs)

    except Exception as e:
        print(f"An error occurred during execution: {e}")

    finally:
        sys.stdout = old_stdout

    ans = captured_output.getvalue()
    print("------Code output------")
    print(ans)

    return ans

@tool
def execute_analysis_tool(code: str, filepath: str) -> str:
    """
    Executes Python code and returns the output. Used for simple data analysis.
    The generated code must define a function named 'process_data'
    that accepts a single argument: file_path.
    """
    print("Pre-processor is executing analysis code")

    return execute_analysis(
        code,
        filepath,
        target_function="process_data"
    )