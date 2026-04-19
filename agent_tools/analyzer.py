
import os
import re
import warnings
import pandas as pd
from google import genai
from dotenv import load_dotenv
from .llm_model import model
import json
from pipeline.state import sanitize_for_state


def _repair_deprecated_pandas_offsets(code: str) -> str:
    """
    Patch common pandas 2.2+ deprecated offset aliases in generated analysis code.

    Keep this narrow and mechanical so it only fixes known runtime breakages.
    """
    repaired = code
    repaired = repaired.replace("resample('M')", "resample('ME')")
    repaired = repaired.replace('resample("M")', 'resample("ME")')
    repaired = repaired.replace("freq='M'", "freq='ME'")
    repaired = repaired.replace('freq="M"', 'freq="ME"')
    repaired = repaired.replace("freq = 'M'", "freq = 'ME'")
    repaired = repaired.replace('freq = "M"', 'freq = "ME"')
    return repaired


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


def generate_analysis_code(user_question, data_path=None, data_paths_dict=None):
    """
    Generates Python code to analyze the dataset based on the user's question using Gemini.

    Args:
        user_question: The analysis question.
        data_path: Single file path (backward compat, used to build a one-entry dict).
        data_paths_dict: Dict mapping short names to file paths (multi-file).
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    MODEL_ID = os.getenv("MODEL_ID")

    if not api_key:
        return "print('Error: GEMINI_API_KEY not found. Please set it in a .env file.')"

    client = genai.Client(api_key=api_key)

    # Build file_paths dict — always dict-based
    if data_paths_dict:
        file_paths = data_paths_dict
    elif data_path:
        stem = os.path.splitext(os.path.basename(data_path))[0]
        file_paths = {stem: data_path}
    else:
        print("Error: No data path provided")
        return

    # Validate all paths exist and read headers
    dataset_sections = []
    for name, path in file_paths.items():
        if not os.path.exists(path):
            print(f'Error: Data file not found at {path}')
            return
        ext = os.path.splitext(path)[1].lower()
        read_fn = "pd.read_csv" if ext == ".csv" else "pd.read_json"
        try:
            df = pd.read_csv(path) if ext == ".csv" else pd.read_json(path)
            df_header = df.columns.tolist()
            df_first_rows = df.head(5).to_string()
        except Exception as e:
            print(f'Error reading data file {path}: {e}')
            return
        dataset_sections.append(
            f'  "{name}": "{path}"\n'
            f"    Format: {'CSV' if ext == '.csv' else 'JSON'} (load with {read_fn})\n"
            f"    Columns: {df_header}\n"
            f"    First 5 rows:\n{df_first_rows}"
        )

    is_multi = len(file_paths) > 1
    dataset_text = "DATASETS (file_paths dict):\n" + "\n\n".join(dataset_sections)

    if is_multi:
        load_instruction = (
            "Load files with pd.read_json(file_paths['<name>']).\n"
            "If your analysis requires combining files, use pd.merge() on appropriate key columns."
        )
        example_load = '    df_sales = pd.read_json(file_paths["sales"])\n    df_products = pd.read_json(file_paths["products"])\n    df = pd.merge(df_sales, df_products, on="product_id")'
    else:
        first_name = next(iter(file_paths))
        load_instruction = f'Load the file with pd.read_json(file_paths["{first_name}"]).'
        example_load = f'    df = pd.read_json(file_paths["{first_name}"])'

    prompt = f"""You are a Python data analyst. Write a single function that executes ALL of the analysis steps listed below and emits structured JSON.

{dataset_text}

{load_instruction}

USER QUESTION: "{user_question}"

REQUIRED FUNCTION SIGNATURE:
def analyze_spending_data(file_paths):
    # file_paths is a dict mapping names to JSON file paths

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
- If you resample monthly data, use pandas 'ME' instead of deprecated 'M'
- If you use pd.Grouper with monthly frequency, use freq='ME'
- For categorical/ranking: sort descending by value; keep top 14, collapse the rest into an "Other" entry
- The LAST line of the function must be: import json; print(json.dumps(results))
- Do NOT print anything else inside the function
- Do NOT use markdown fences in your output

EXAMPLE:

def analyze_spending_data(file_paths):
    import pandas as pd
    import json

{example_load}

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
        response = _repair_deprecated_pandas_offsets(response)
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

    def _run_once(code_to_run):
        exec(code_to_run, exec_globals)

        functions = {
            name: obj
            for name, obj in exec_globals.items()
            if callable(obj) and inspect.isfunction(obj)
        }

        if not functions:
            print("No functions found in generated code.")
            return captured_output.getvalue()

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

        sig = inspect.signature(target_fn)
        try:
            sig.bind(*args, **kwargs)
        except TypeError as bind_error:
            print(f"Argument mismatch: {bind_error}")
            return captured_output.getvalue()

        target_fn(*args, **kwargs)

    try:
        # Execute generated code
        _run_once(code)

    except Exception as e:
        if "Invalid frequency: M" in str(e):
            repaired_code = _repair_deprecated_pandas_offsets(code)
            if repaired_code != code:
                print("Retrying analysis after patching deprecated pandas monthly frequency aliases.")
                exec_globals = {}
                try:
                    _run_once(repaired_code)
                except Exception as retry_error:
                    print(f"An error occurred during execution: {retry_error}")
            else:
                print(f"An error occurred during execution: {e}")
        else:
            print(f"An error occurred during execution: {e}")

    finally:
        sys.stdout = old_stdout

    ans = captured_output.getvalue()
    print("------Code output------")
    print(ans)

    parsed = _extract_json_from_output(ans)
    if parsed is not None:
        return sanitize_for_state(parsed)
    warnings.warn("No JSON emitted; falling back to raw string", RuntimeWarning)
    return ans
