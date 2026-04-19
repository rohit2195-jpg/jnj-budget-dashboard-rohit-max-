from langchain.agents import create_agent
from langchain.tools import tool
import json
import os
from dotenv import load_dotenv
from agent_tools.tools import generate_analysis_code_tool, execute_analysis_tool
from agent_tools.llm_model import code_llm


load_dotenv()


agent = create_agent(code_llm, tools=[generate_analysis_code_tool, execute_analysis_tool])


def _build_file_paths_dict(manifest, manifests=None):
    """Build a {name: path} dict from manifest(s) for the analyzer tools."""
    if manifests and len(manifests) > 1:
        result = {}
        seen = {}
        for m in manifests:
            dp = m["data_path"]
            stem = os.path.splitext(os.path.basename(dp))[0]
            if stem in seen:
                seen[stem] += 1
                stem = f"{stem}_{seen[stem]}"
            else:
                seen[stem] = 0
            result[stem] = dp
        return result
    dp = manifest["data_path"]
    stem = os.path.splitext(os.path.basename(dp))[0]
    return {stem: dp}


def _describe_dataset_loads(file_paths_dict):
    dataset_loaders = {}
    dataset_lines = []
    for name, path in file_paths_dict.items():
        ext = os.path.splitext(path)[1].lower()
        loader = "pd.read_csv" if ext == ".csv" else "pd.read_json"
        dataset_loaders[name] = loader
        dataset_lines.append(f'- File "{name}": {path} (load with {loader})')
    return dataset_loaders, dataset_lines


def _extract_text_content(message) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                if text:
                    parts.append(str(text))
            elif item:
                parts.append(str(item))
        return "\n".join(parts)
    return "" if content is None else str(content)


def callAgent(question, manifest, plan, manifests=None):
    # Build file_paths dict (always dict-based)
    file_paths_dict = _build_file_paths_dict(manifest, manifests)
    file_paths_json = json.dumps(file_paths_dict)
    dataset_loaders, dataset_load_lines = _describe_dataset_loads(file_paths_dict)

    # Build dataset description — multi-file or single
    if manifests and len(manifests) > 1:
        dataset_lines = []
        for i, m in enumerate(manifests, 1):
            name = os.path.splitext(os.path.basename(m["data_path"]))[0]
            loader = dataset_loaders.get(name, "pd.read_json")
            dataset_lines.append(
                f"- File \"{name}\": {m['data_path']}\n"
                f"  Load with: {loader}\n"
                f"  Columns: {m.get('columns', [])}\n"
                f"  Column types: {m.get('dtypes', {})}\n"
                f"  Row count: {m.get('row_count', 'unknown')}"
            )
        dataset_section = "Datasets (file_paths dict):\n" + "\n".join(dataset_lines)
        load_hint = (
            "Load each file using the loader shown next to its path. "
            "If your analysis requires combining files, use pd.merge() on appropriate key columns."
        )
    else:
        first_name = next(iter(file_paths_dict))
        m = manifest
        loader = dataset_loaders[first_name]
        dataset_section = (
            f"Dataset:\n"
            f"- file_paths dict: {file_paths_json}\n"
            f"- Load with: {loader}\n"
            f"- Columns: {m.get('columns', [])}\n"
            f"- Column types: {m.get('dtypes', {})}\n"
            f"- Row count: {m.get('row_count', 'unknown')}"
        )
        load_hint = f'Load the file with {loader}(file_paths["{first_name}"]).'

    # Format the checklist so the analyst executes every step
    checklist_lines = "\n".join(
        f"  {step['id']}. [{step['output_label']}] {step['description']}"
        for step in plan.get("analyses", [])
    )

    analysis_output = agent.invoke(
        {
            "messages": [
                {
                    "role": "system",
                    "content": f"""You are a data analyst. Use your tools to execute EVERY step in the analysis checklist.

The generated code must define a function named 'analyze_spending_data(file_paths)' that:
1. Accepts file_paths as a dict mapping short names to JSON file paths
2. Accepts CSV and JSON datasets and loads each file with the correct pandas reader for that file extension
3. {load_hint}
4. Performs ALL checklist steps using pandas
5. Builds a `results` dict keyed by each step's output_label
6. Each value in `results` must follow this typed schema:
   {{
     "type": "<categorical|timeseries|ranking|comparison|scalar|scatter>",
     "title": "<human-readable title>",
     "description": "<what was computed>",
     "unit": "<USD|count|percent|etc>",
     // For categorical/ranking/timeseries:
     "categories": ["label1", "label2", ...],
     "values": [num1, num2, ...],
     // For comparison (multiple series):
     "categories": ["label1", ...],
     "series": [{{"name": "Series A", "data": [num1, ...]}}, ...]
   }}
7. Converts all numpy types with .item() or float() before inserting into results
8. If monthly resampling is needed, use pandas 'ME' instead of deprecated 'M'
9. Ends with: import json; print(json.dumps(results))
10. For categorical/ranking results, include at most 15 items sorted by value descending.
   If the data has more than 15 categories, sum the remaining values into a single final
   entry labelled "Other".

IMPORTANT: When calling the tools, pass the file_paths dict as a JSON string: {file_paths_json}

WHAT WRONG OUTPUT LOOKS LIKE — do not do this:
  BAD: "type": "bar"           → "bar" is a chart type; use "categorical" or "ranking"
  BAD: results["result1"] = …  → key must match output_label exactly
  BAD: "values": [np.int64(x)] → convert all numpy types: float(x) or x.item()
  BAD: "type": "comparison", "values": [...]  → comparison needs "series": [{{name, data}}]
  BAD: df.resample("M")        → monthly resampling must use "ME"

BEFORE writing each results entry, ask:
  1. Is this one number? → scalar
  2. Is this a list paired with labels? → categorical, ranking, or timeseries
  3. Is this multiple named series? → comparison
  4. Is this x/y point pairs? → scatter

Only call tools to run code. Do not output commentary.
"""
                },
                {
                    "role": "user",
                    "content": f"""User question: {question}

{dataset_section}

file_paths JSON for tool calls: {file_paths_json}
Dataset load instructions:
{chr(10).join(dataset_load_lines)}

Analysis checklist — execute ALL of these steps in order:
{checklist_lines}

Use the file_paths dict above directly. Do not look for different paths.

IMPORTANT: The `results` dict MUST have a key for each output_label listed above: {[step['output_label'] for step in plan.get('analyses', [])]}.
The final line of analyze_spending_data MUST be: import json; print(json.dumps(results))
"""
                }
            ]
        }
    )

    messages = analysis_output.get("messages", []) if isinstance(analysis_output, dict) else []

    # The LLM's final message after tool use is often empty — the real analysis
    # output is in the ToolMessage returned by execute_analysis_tool.
    # Extract it by matching tool_call_ids from AIMessage.tool_calls.
    result = _extract_execute_tool_output(messages)
    if result.strip():
        from agent_tools.analyzer import _extract_json_from_output
        parsed = _extract_json_from_output(result)
        return parsed if parsed is not None else result

    # Fallback: last message content (handles cases where no tool was called)
    if messages:
        content = _extract_text_content(messages[-1]).strip()
        if content:
            return content
        for msg in reversed(messages[:-1]):
            content = _extract_text_content(msg).strip()
            if content:
                return content

    return _extract_text_content(analysis_output)


def _extract_execute_tool_output(messages) -> str:
    """
    Walk the agent message history and return the captured stdout from every
    execute_analysis_tool call, joined together.

    LangChain message structure after tool use:
      AIMessage(tool_calls=[{name, args, id}])  ← agent decides to call a tool
      ToolMessage(content=..., tool_call_id=id) ← tool result
      AIMessage(content="")                     ← LLM acknowledgment (often empty)

    We want the ToolMessage content for execute_analysis_tool, not the final AIMessage.
    """
    # Step 1: collect IDs of every execute_analysis_tool call
    execute_ids = set()
    for msg in messages:
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            continue
        for tc in tool_calls:
            name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
            tc_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")
            if name == "execute_analysis_tool":
                execute_ids.add(tc_id)

    # Step 2: find ToolMessages whose tool_call_id matches
    # Collect all outputs but prefer the last one that contains valid JSON,
    # since earlier executions may have failed and produced error strings.
    results = []
    for msg in messages:
        tool_call_id = getattr(msg, "tool_call_id", None)
        if tool_call_id and tool_call_id in execute_ids:
            content = _extract_text_content(msg)
            if content:
                results.append(content)

    if not results:
        return ""

    # Return only the last execution output — if the agent retried after a
    # failure, the last output is the corrected one and earlier outputs
    # contain error messages that confuse downstream JSON parsing.
    return results[-1]
