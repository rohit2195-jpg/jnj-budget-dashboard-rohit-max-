
import os
import pandas as pd
from google import genai
from dotenv import load_dotenv
from .llm_model import model
import json


def generate_analysis_code(user_question, data_path):
    """
    Generates Python code to analyze the dataset based on the user's question using Gemini.
    """
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
        df_header = pd.read_json(data_path).columns.tolist()
        df_first_rows = pd.read_json(data_path).head(5).to_string()
    except Exception as e:
        print(f'Error reading data file: {e}')
        return 

    prompt = f"""
    You are a data analyst. Your task is to write Python code to answer a user's question about a dataset.
    The dataset is located at: {data_path}
    The data is in JSON format and its columns are: {df_header}
    First five rows in the data: {df_first_rows}

    User's question: "{user_question}"

    Based on the user's question, please generate a Python script that uses the pandas library to perform the analysis.
    The script should:
    1. Load the JSON data from the specified path.
    2. Perform the analysis required to answer the user's question.
    3. Print the results of the analysis to the console.

    Generate ONLY this function:

    def analyze_spending_data(file_path):

    The function must:
    - Load JSON from file_path
    - Perform analysis
    - Print insights
    

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
    from io import StringIO
    import sys
    import inspect

    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    exec_globals = {}

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
