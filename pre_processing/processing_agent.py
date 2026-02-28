from langchain.agents import create_agent
from langchain.tools import tool
from pathlib import Path
from datetime import datetime
import json
import os
import pandas as pd
from dotenv import load_dotenv
from agent_tools.llm_model import code_llm
from pre_processing.tools import generate_analysis_code, execute_analysis_tool, _compute_output_path, _compute_manifest_path, compute_file_hash

load_dotenv()


pre_process_agent = create_agent(code_llm, tools=[generate_analysis_code, execute_analysis_tool])


def callPreProcessAgent(data_path):
    # Compute output path deterministically in Python — no LLM involvement
    output_path = _compute_output_path(data_path)
    manifest_path = _compute_manifest_path(data_path)
    file_hash = compute_file_hash(data_path)

    # Cache hit: skip all LLM calls if file hasn't changed
    if os.path.exists(manifest_path) and os.path.exists(output_path):
        with open(manifest_path) as f:
            cached = json.load(f)
        if cached.get("file_hash") == file_hash:
            print(f"Cache hit for {data_path} — skipping preprocessing")
            return cached

    analysis_output = pre_process_agent.invoke(
        {"messages": [{"role": "user",
                       "content": f"""Please pre-process the data by cleaning, transforming, and organizing raw data into a usable format for future analysis.
            Data path: {data_path}
            IMPORTANT: The cleaned dataset MUST be saved to EXACTLY this path: {output_path}
            Do not choose a different filename. Use exactly: {output_path}

            Steps:
            1. Use the generate_analysis_code tool with the data path to generate preprocessing code.
            2. Use the execute_analysis_tool to run the code and save the cleaned dataset.
            3. In your final answer, provide a brief overview of the dataset (columns, shape, notable characteristics).
               Do not repeat the code. Do not mention the file path — that is handled separately.

            The generated code must define a function named 'process_data'. This will be the top level function.
            """
                       }]}
    )

    last_message = analysis_output["messages"][-1]
    content = last_message.content
    if isinstance(content, list):
        summary = content[0].get("text", "")
    elif isinstance(content, str):
        summary = content
    else:
        summary = str(content)

    # Build the manifest in Python — reliable, no LLM text parsing
    if not os.path.exists(output_path):
        return {
            "data_path": output_path,
            "source_file": data_path,
            "status": "error",
            "summary": summary,
            "error": f"Preprocessing did not produce expected output file at: {output_path}"
        }

    df = pd.read_json(output_path)
    manifest = {
        "data_path": output_path,
        "source_file": data_path,
        "columns": df.columns.tolist(),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "row_count": len(df),
        "summary": summary,
        "created_at": datetime.utcnow().isoformat(),
        "status": "success",
        "file_hash": file_hash,
    }

    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    print(f"Manifest written to {manifest_path}")
    return manifest
