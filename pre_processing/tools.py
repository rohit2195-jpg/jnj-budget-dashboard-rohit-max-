
import os
import pandas as pd
from google import genai
from dotenv import load_dotenv
from agent_tools.llm_model import model
from langchain.tools import tool
import json


@tool
def generate_analysis_code(data_path:str) -> str:
    """
    Generates Python code to pre-process the dataset. Will print saved location of processed dataset.
    """
    print("Pre-processing generating cleaning code")
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    MODEL_ID = os.getenv("MODEL_ID")

    if not api_key:
        return "print('Error: GEMINI_API_KEY not found. Please set it in a .env file.')"

    client = genai.Client(api_key=api_key)

    # Ensure the data path is valid
    if not os.path.exists(data_path):
        print(f'Error: Data file not found at {data_path}')
        return 

    # Get the header of the CSV for context
    try:
        df = pd.read_json(data_path)
        df_header = pd.read_json(data_path).columns.tolist()
        df_first_rows = pd.read_json(data_path).head(5).to_string()
        info = df
    except Exception as e:
        print(f'Error reading data file: {e}')
        return 

    prompt = f"""
    You are a data pre-processor
    The dataset is located at: {data_path}
    The data is in JSON format and its columns are: {df_header}
    First five rows in the data: {df_first_rows}

    Please pre-process the data by cleaning, transforming, and organizing raw data into a usable format for future analysis and machine learning
    Hardcode the data path in your code.

    Based on the user's question, please generate a Python script that uses the pandas library to perform the analysis.
    The script should:
    1. Load the JSON data from the specified path.
    2. Write code to pre-process, and clean the data
    3. Get some understanding of the dataset
    4. Save cleaned dataset to 'pre_processing/processed_data/[file_name_here]' as a json file
    5. Print path of the cleaned dataset ex. (pre_processing/processed_data/[file_name_here])


    Your code should be executable and self-contained. Do not include any markdown formatting.
    """

    try:
        response = model.invoke(prompt)
        
        # clean response
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