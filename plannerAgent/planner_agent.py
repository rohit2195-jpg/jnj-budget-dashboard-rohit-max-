import json
from langchain_core.messages import SystemMessage, HumanMessage
from agent_tools.llm_model import model


PLANNER_SYSTEM = """You are a precision data analysis planner. Your sole output is a JSON object containing a numbered list of concrete, executable pandas analysis steps.

NEVER write vague steps like these:
  BAD: "Analyze the data to find patterns"
  BAD: "Look at spending over time"
  BAD: "Examine recipient information"

ALWAYS write steps that name exact columns and operations:
  GOOD: "Group by 'Recipient Name', sum 'Award Amount', sort descending, take top 15"
  GOOD: "Parse 'Start Date' to datetime, resample by year ('Y'), sum 'Award Amount', return as timeseries"
  GOOD: "For each unique 'team_name', compute mean of 'lap_time_sec'; rank ascending"

OUTPUT FORMAT — return only this JSON, no other text:
{
    "analyses": [
        {"id": 1, "description": "<concrete step>", "output_label": "<short title>"},
        ...
    ]
}"""


def create_analysis_plan(user_question: str, manifest: dict,
                         is_followup: bool = False,
                         conversation_history: list | None = None) -> dict:
    """
    Generates a structured checklist of specific pandas analysis steps
    based on the user question and dataset schema.

    When is_followup is True, produces a focused 1-2 step plan that avoids
    repeating prior analyses listed in conversation_history.

    Returns a dict:
    {
        "analyses": [
            {"id": 1, "description": "...", "output_label": "..."},
            ...
        ]
    }
    """
    columns = manifest.get("columns", [])
    dtypes = manifest.get("dtypes", {})
    row_count = manifest.get("row_count", "unknown")
    summary = manifest.get("summary", "")

    if is_followup and conversation_history:
        history_text = "\n".join(
            f"  - Q: \"{h['question']}\" → {h.get('summary_snippet', 'completed')}"
            for h in (conversation_history or [])[-5:]
        )
        user_msg = f"""This is a FOLLOW-UP question about a dataset that has already been analyzed.

Previous analyses performed:
{history_text}

The user now asks: "{user_question}"

Dataset schema:
- Columns: {columns}
- Column types: {dtypes}
- Row count: {row_count}

Generate 1 to 2 focused analysis steps that answer ONLY this follow-up question.
Do NOT repeat any analysis already performed above.
Rules:
- Use only column names listed above
- Limit any step aggregating many categories to "top 15 X by Y"
- Output ONLY the JSON object. No markdown fences, no explanation."""
    else:
        user_msg = f"""User question: "{user_question}"

Dataset schema:
- Columns: {columns}
- Column types: {dtypes}
- Row count: {row_count}
- Dataset summary: {summary}

Generate 3 to 6 analysis steps that together fully answer the user question.
Rules:
- Use only column names listed above
- Start with the most direct answer, then add supporting context
- If date/time columns exist, include at least one time-series step
- If category + numeric columns exist, include at least one ranking/aggregation step
- Limit any step aggregating many categories to "top 15 X by Y"
- Output ONLY the JSON object. No markdown fences, no explanation."""

    response = model.invoke([SystemMessage(content=PLANNER_SYSTEM), HumanMessage(content=user_msg)])
    # Handle both AIMessage.content and raw .text depending on LangChain version
    raw = response.content if hasattr(response, "content") else response.text
    if isinstance(raw, list):
        raw = raw[0].get("text", "") if raw else ""
    text = raw.strip().strip("```").lstrip("json").strip()

    try:
        plan = json.loads(text)
        if "analyses" not in plan or not isinstance(plan["analyses"], list) or not plan["analyses"]:
            raise ValueError("plan missing analyses list")
    except (json.JSONDecodeError, ValueError):
        # Fallback: single generic step so the pipeline never breaks
        plan = {
            "analyses": [
                {
                    "id": 1,
                    "description": f"Perform analysis to answer: {user_question}",
                    "output_label": "Analysis Result"
                }
            ]
        }

    print("--- Analysis Plan ---")
    for step in plan["analyses"]:
        print(f"  {step['id']}. [{step['output_label']}] {step['description']}")
    print("---------------------")

    return plan
