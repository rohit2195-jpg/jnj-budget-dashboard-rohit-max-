import json
from agent_tools.llm_model import model


def create_analysis_plan(user_question: str, manifest: dict) -> dict:
    """
    Generates a structured checklist of specific pandas analysis steps
    based on the user question and dataset schema.

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

    prompt = f"""You are an expert data analysis planner.

Your job is to break down a user's question into a precise, ordered checklist of specific pandas analysis steps.
Each step must reference the actual column names from the dataset schema below.

User question: "{user_question}"

Dataset schema:
- Columns: {columns}
- Column types: {dtypes}
- Row count: {row_count}
- Dataset summary: {summary}

Generate a JSON object with this exact structure:
{{
    "analyses": [
        {{
            "id": 1,
            "description": "exact pandas operation using real column names from the schema",
            "output_label": "short label for this result (used in graph titles and report headings)"
        }}
    ]
}}

Rules:
- Each step must be concrete and specific — never vague like "analyze the data"
- Use the actual column names listed above
- Generate 3 to 6 steps that together fully answer the user question
- Start with the most direct answer to the question, then add supporting context
- If date/time columns are present, include at least one trend or time-series step
- If category + numeric columns are present, include at least one ranking or aggregation step
- Steps may reference results from previous steps (e.g. "using the top 10 from step 1...")
- If a step aggregates across many categories (e.g. by sub-agency, by vendor, by region),
  limit it to the top 15 most significant items by value. Phrase the description as
  "top 15 X by Y" so the analyst knows to truncate.
- Output ONLY the JSON object. No markdown fences, no explanation, no extra text.
"""

    response = model.invoke(prompt)
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
