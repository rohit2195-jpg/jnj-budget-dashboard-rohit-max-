from langchain.agents import create_agent
from langchain.tools import tool
import os
from dotenv import load_dotenv
from agent_tools.tools import generate_analysis_code_tool, execute_analysis_tool
from agent_tools.llm_model import code_llm


load_dotenv()


agent = create_agent(code_llm, tools=[generate_analysis_code_tool, execute_analysis_tool])


def callAgent(question, manifest, plan):
    # Extract structured fields from the manifest — no LLM text parsing needed
    data_path = manifest["data_path"]
    columns = manifest.get("columns", [])
    dtypes = manifest.get("dtypes", {})
    row_count = manifest.get("row_count", "unknown")
    summary = manifest.get("summary", "")

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
                    "content": """You are a data analyst. Use your tools to execute EVERY step in the analysis checklist.

The generated code must define a function named 'analyze_spending_data(file_path)' that:
1. Performs ALL checklist steps using pandas
2. Builds a `results` dict keyed by each step's output_label
3. Each value in `results` must follow this typed schema:
   {
     "type": "<categorical|timeseries|ranking|comparison|scalar|scatter>",
     "title": "<human-readable title>",
     "description": "<what was computed>",
     "unit": "<USD|count|percent|etc>",
     // For categorical/ranking/timeseries:
     "categories": ["label1", "label2", ...],
     "values": [num1, num2, ...],
     // For comparison (multiple series):
     "categories": ["label1", ...],
     "series": [{"name": "Series A", "data": [num1, ...]}, ...]
   }
4. Converts all numpy types with .item() or float() before inserting into results
5. Ends with: import json; print(json.dumps(results))
6. For categorical/ranking results, include at most 15 items sorted by value descending.
   If the data has more than 15 categories, sum the remaining values into a single final
   entry labelled "Other".

Only call tools to run code. Do not output commentary.
"""
                },
                {
                    "role": "user",
                    "content": f"""User question: {question}

Dataset:
- Path: {data_path}
- Columns: {columns}
- Column types: {dtypes}
- Row count: {row_count}

Analysis checklist — execute ALL of these steps in order:
{checklist_lines}

Use the data path above directly. Do not look for a different path.

IMPORTANT: The `results` dict MUST have a key for each output_label listed above: {[step['output_label'] for step in plan.get('analyses', [])]}.
The final line of analyze_spending_data MUST be: import json; print(json.dumps(results))
"""
                }
            ]
        }
    )

    messages = analysis_output["messages"]

    # The LLM's final message after tool use is often empty — the real analysis
    # output is in the ToolMessage returned by execute_analysis_tool.
    # Extract it by matching tool_call_ids from AIMessage.tool_calls.
    result = _extract_execute_tool_output(messages)
    if result.strip():
        from agent_tools.analyzer import _extract_json_from_output
        parsed = _extract_json_from_output(result)
        return parsed if parsed is not None else result

    # Fallback: last message content (handles cases where no tool was called)
    last_message = messages[-1]
    content = last_message.content
    if isinstance(content, list):
        return content[0].get("text", "")
    return content


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
    results = []
    for msg in messages:
        tool_call_id = getattr(msg, "tool_call_id", None)
        if tool_call_id and tool_call_id in execute_ids:
            content = msg.content
            if isinstance(content, list):
                content = content[0].get("text", "") if content else ""
            if content:
                results.append(content)

    return "\n\n".join(results)
