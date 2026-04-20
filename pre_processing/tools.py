
import os
import hashlib
from pathlib import Path
import json
import pandas as pd
from google import genai
from dotenv import load_dotenv
from agent_tools.llm_model import model
from langchain.tools import tool


def _path_suffix(data_path: str) -> str:
    """Add a short path-based suffix so same-named files in different folders do not collide."""
    normalized = Path(data_path).as_posix().lower()
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()[:8]


def _compute_output_path(data_path: str) -> str:
    """Deterministically compute the cleaned output path from the input path."""
    safe_stem = Path(data_path).stem.replace(" ", "_")
    return f"pre_processing/processed_data/cleaned_{safe_stem}_{_path_suffix(data_path)}.json"


def _compute_manifest_path(data_path: str) -> str:
    """Deterministically compute the per-file manifest path from the input path."""
    safe_stem = Path(data_path).stem.replace(" ", "_")
    return f"pre_processing/processed_data/cleaned_{safe_stem}_{_path_suffix(data_path)}_manifest.json"


def compute_file_hash(data_path: str) -> str:
    """Compute MD5 hex digest of a file, reading in chunks."""
    h = hashlib.md5()
    with open(data_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_dataframe_for_path(data_path: str) -> pd.DataFrame:
    """
    Load a CSV/JSON dataframe defensively.

    LLM-generated preprocessing code is instructed to save JSON records, but in
    practice pandas can still emit line-delimited JSON or other JSON shapes.
    Fall back through the common variants before surfacing an exception.
    """
    if data_path.lower().endswith('.csv'):
        return pd.read_csv(data_path)

    try:
        return pd.read_json(data_path)
    except ValueError as first_error:
        errors = [f"default read_json failed: {first_error}"]

        try:
            return pd.read_json(data_path, lines=True)
        except ValueError as second_error:
            errors.append(f"lines=True failed: {second_error}")

        with open(data_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)

        if isinstance(raw, list):
            return pd.DataFrame(raw)
        if isinstance(raw, dict):
            if all(isinstance(value, list) for value in raw.values()):
                return pd.DataFrame(raw)
            return pd.DataFrame([raw])

        raise ValueError("; ".join(errors) + f"; unsupported JSON payload type: {type(raw).__name__}")


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
        df = load_dataframe_for_path(data_path)
        df_header = df.columns.tolist()
        df_first_rows = df.head(5).to_string()
    except Exception as e:
        print(f'Error reading data file: {e}')
        return

    prompt = f"""You are a Python data preprocessing engineer. Output only executable Python code — no markdown, no explanation.

TASK: Write a function named `process_data(file_path)` that cleans the dataset and saves it as JSON.

DATASET:
- Input path: {data_path}
- Columns: {df_header}
- First 5 rows:
{df_first_rows}

REQUIRED TEMPLATE (fill in only the cleaning steps section):

def process_data(file_path):
    import pandas as pd
    import os

    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_json(file_path)

    # --- CLEANING STEPS ---
    # 1. Drop duplicate rows
    # 2. Handle nulls (drop or fill based on column semantics)
    # 3. Fix dtypes (parse date strings, coerce numerics)
    # 4. Avoid chained assignment and avoid inplace=True on Series methods
    #    Example: use df[col] = df[col].fillna(value) instead of df[col].fillna(value, inplace=True)
    # IMPORTANT: Do NOT rename columns — downstream code uses the original names: {df_header}

    os.makedirs('pre_processing/processed_data', exist_ok=True)
    df.to_json('{output_path}', orient='records', indent=2)

    print(f"Cleaned: {{df.shape[0]}} rows x {{df.shape[1]}} columns")
    print(f"Columns: {{df.columns.tolist()}}")

Output ONLY the complete function. No imports outside the function body. No markdown fences."""

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
