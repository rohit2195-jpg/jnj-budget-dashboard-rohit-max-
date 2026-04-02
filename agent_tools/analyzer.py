
import os
import re
import warnings
import pandas as pd
from google import genai
from dotenv import load_dotenv
from .llm_model import model
import json


def _extract_json_from_output(raw: str):
    """
    Try to find a JSON dict in raw captured stdout.

    Strategy 1: scan lines from bottom up for any line that starts with '{'
                and parses as a JSON dict (handles single-line JSON).
    Strategy 2: find all top-level '{' positions, try parsing from each
                (last-first) to handle multiline/indented JSON.

    Returns dict on success, None on failure.
    """
    if not raw:
        return None

    # Strategy 1: bottom-up line scan (fast path for single-line JSON)
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

    # Strategy 2: find all '{' at the start of a line, try parsing from each
    # position (last occurrence first) to prefer the final JSON output
    candidates = [m.start() for m in re.finditer(r'^\s*\{', raw, re.MULTILINE)]
    for pos in reversed(candidates):
        try:
            parsed = json.loads(raw[pos:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            # The slice may have trailing text; try to find the matching '}'
            depth = 0
            for i, ch in enumerate(raw[pos:]):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            parsed = json.loads(raw[pos:pos + i + 1])
                            if isinstance(parsed, dict):
                                return parsed
                        except json.JSONDecodeError:
                            break
                        break

    return None


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

    prompt = f"""You are a Python data analyst. Write a single function that executes ALL of the analysis steps listed below and emits structured JSON.

DATASET
- Path: {data_path}
- Format: JSON (load with pd.read_json)
- Columns: {df_header}
- First 5 rows:
{df_first_rows}

USER QUESTION: "{user_question}"

REQUIRED FUNCTION SIGNATURE:
def analyze_spending_data(file_path):

OUTPUT SCHEMA — build a dict called `results`, keyed by output_label strings.
Each value must be one of these typed structures:

  categorical / ranking:
    {{"type": "categorical", "title": "...", "description": "...", "unit": "USD",
      "categories": ["A", "B"], "values": [1000.0, 500.0]}}

  timeseries:
    {{"type": "timeseries", "title": "...", "description": "...", "unit": "count",
      "categories": ["2022", "2023", "2024"], "values": [10, 15, 12]}}

  comparison (multiple series):
    {{"type": "comparison", "title": "...", "description": "...", "unit": "USD",
      "categories": ["Q1", "Q2"],
      "series": [{{"name": "GroupA", "data": [100.0, 200.0]}}, {{"name": "GroupB", "data": [80.0, 160.0]}}]}}

  scalar:
    {{"type": "scalar", "title": "...", "description": "...", "unit": "USD", "value": 1234567.89}}

  scatter:
    {{"type": "scatter", "title": "...", "description": "...", "unit": "USD",
      "data": [{{"x": 1.0, "y": 2.0}}, {{"x": 3.0, "y": 4.0}}]}}

RULES:
- Convert ALL numpy types with .item() or float() before storing in results
- For categorical/ranking: sort descending by value; keep top 14, collapse the rest into an "Other" entry
- The LAST line of the function must be: import json; print(json.dumps(results))
- Do NOT print anything else inside the function
- Do NOT use markdown fences in your output

EXAMPLE (dataset with columns ["Recipient Name", "Award Amount", "Start Date"]):

def analyze_spending_data(file_path):
    import pandas as pd
    import json

    df = pd.read_json(file_path)

    top = df.groupby("Recipient Name")["Award Amount"].sum().sort_values(ascending=False).head(14)
    others = df.groupby("Recipient Name")["Award Amount"].sum().sort_values(ascending=False).iloc[14:].sum()
    cats = top.index.tolist() + (["Other"] if others > 0 else [])
    vals = [float(v) for v in top.values] + ([float(others)] if others > 0 else [])

    results = {{
        "Top Recipients by Award Amount": {{
            "type": "ranking",
            "title": "Top Recipients by Award Amount",
            "description": "Sum of Award Amount per recipient, top 14 plus Other",
            "unit": "USD",
            "categories": cats,
            "values": vals
        }},
        "Total Awarded": {{
            "type": "scalar",
            "title": "Total Awarded",
            "description": "Sum of all award amounts in the dataset",
            "unit": "USD",
            "value": float(df["Award Amount"].sum())
        }}
    }}
    import json; print(json.dumps(results))
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

    parsed = _extract_json_from_output(ans)
    if parsed is not None:
        return parsed
    warnings.warn("No JSON emitted; falling back to raw string", RuntimeWarning)
    return ans
