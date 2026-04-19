from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from pipeline.state import (
    PipelineState,
    serialize_analysis_output,
    get_all_data_paths,
    get_all_manifests,
    sanitize_for_state,
)

# Existing agent imports
from pre_processing.processing_agent import callPreProcessAgent
from plannerAgent.planner_agent import create_analysis_plan
from agent_tools.agent import callAgent
from forecastAgent.forecast_agent import create_forecast
from graphAgent.graphAgent import create_graph
from summarizerAgent.summarizer_agent import summarize_results, generate_followup_explanation


# ─────────────────────────────────────────────────────────────────────────────
# NODES
# Each node receives the full PipelineState and returns a partial dict of only
# the keys it changed. LangGraph merges partial updates into the state.
# ─────────────────────────────────────────────────────────────────────────────

def entry_router_node(state: PipelineState) -> dict:
    """Pass-through node; routing is handled by conditional edges."""
    return {}


def preprocess_node(state: PipelineState) -> dict:
    """
    Run callPreProcessAgent for each file in data_paths.
    Success → {"manifest": <dict>, "manifests": [<dict>, ...]}
    Failure → {"error": <str>}
    """
    try:
        data_paths = get_all_data_paths(state)
        manifests = []
        for dp in data_paths:
            manifest = callPreProcessAgent(dp)
            if manifest.get("status") == "error":
                return {"error": f"Preprocessing failed for {dp}: {manifest.get('error', 'unknown')}"}
            manifests.append(sanitize_for_state(manifest))
        return {"manifests": manifests, "manifest": manifests[0], "error": None}
    except Exception as exc:
        return {"error": f"Preprocessing exception: {exc}"}


def plan_node(state: PipelineState) -> dict:
    """
    Run create_analysis_plan with question + manifest.
    Success → {"plan": <dict>}
    Failure → {"error": <str>}
    """
    try:
        manifests = get_all_manifests(state)
        plan = create_analysis_plan(
            state["question"],
            state["manifest"],
            is_followup=state.get("is_followup", False),
            conversation_history=state.get("conversation_history"),
            manifests=manifests if len(manifests) > 1 else None,
        )
        if not plan.get("analyses"):
            return {"error": "Planner returned an empty plan."}
        return {"plan": sanitize_for_state(plan), "error": None}
    except Exception as exc:
        return {"error": f"Planning exception: {exc}"}


def human_review_node(state: PipelineState) -> dict:
    """
    Pause execution and surface the analysis plan to the user.

    interrupt(payload) saves the graph state to the checkpointer and raises
    a GraphInterrupt exception that stream()/invoke() catches.  When the graph
    is later resumed with Command(resume=True/False), interrupt() returns that
    value and execution continues normally.
    """
    user_decision = interrupt({
        "plan": state["plan"],
        "question": state["question"],
    })
    return {"approved": bool(user_decision)}


def analyze_node(state: PipelineState) -> dict:
    """
    Run callAgent.
    Success → {"analysis_output": <str>, "error": None}
    Failure → {"error": <str>, "analysis_output": None}
    """
    try:
        manifests = get_all_manifests(state)
        manifest = state.get("manifest") or (manifests[0] if manifests else None)
        if manifest is None:
            return {"error": "No manifest available for analysis.", "analysis_output": None}
        output = callAgent(state["question"], manifest, state["plan"],
                           manifests=manifests if len(manifests) > 1 else None)
        if not output or (isinstance(output, str) and not output.strip()):
            return {
                "error": "Analysis produced empty output.",
                "analysis_output": None,
            }
        if isinstance(output, str) and "An error occurred during execution:" in output:
            return {
                "error": f"Code execution failed: {output[:300]}",
                "analysis_output": None,
            }
        return {"analysis_output": sanitize_for_state(output), "error": None}
    except Exception as exc:
        return {
            "error": f"Analysis exception: {exc}",
            "analysis_output": None,
        }


def retry_bump_node(state: PipelineState) -> dict:
    """
    Increment retry_count and clear error/analysis_output before looping
    back to preprocess.  This keeps routing functions pure (no side effects).
    """
    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "error": None,
        "analysis_output": None,
    }


def forecast_node(state: PipelineState) -> dict:
    """
    Run create_forecast.  Failure is non-fatal — pipeline continues with empty forecasts.
    """
    try:
        serialized = serialize_analysis_output(state.get("analysis_output"))
        forecast_output = create_forecast(state["question"], serialized)
        return {"forecast_output": sanitize_for_state(forecast_output)}
    except Exception as exc:
        return {"forecast_output": {"forecasts": []}, "error": f"Forecast exception: {exc}"}


def graph_gen_node(state: PipelineState) -> dict:
    """
    Run create_graph.  Failure is non-fatal — summarize still runs.
    """
    try:
        serialized = serialize_analysis_output(state.get("analysis_output"))
        forecast_output = state.get("forecast_output")
        prior_chart_ids = state.get("prior_charts") if state.get("is_followup") else None
        graph_data = create_graph(state["question"], serialized, forecast_output, prior_chart_ids=prior_chart_ids)
        return {"graph_data": sanitize_for_state(graph_data)}
    except Exception as exc:
        return {"graph_data": {"charts": []}, "error": f"Graph generation exception: {exc}"}


def summarize_node(state: PipelineState) -> dict:
    """
    Run summarize_results.
    """
    try:
        serialized = serialize_analysis_output(state.get("analysis_output"))
        forecast_output = state.get("forecast_output")
        summary = summarize_results(
            state["question"],
            serialized,
            "analysis_report.md",
            forecast_output,
        )
        return {"summary": str(summary)}
    except Exception as exc:
        return {"error": f"Summarization exception: {exc}"}


def followup_explain_node(state: PipelineState) -> dict:
    """Generate a short 2-4 sentence explanation for follow-up results."""
    try:
        serialized = serialize_analysis_output(state.get("analysis_output"))
        explanation = generate_followup_explanation(
            state["question"],
            serialized,
            state.get("conversation_history"),
        )
        return {"followup_explanation": explanation}
    except Exception as exc:
        return {"followup_explanation": f"Error generating explanation: {exc}"}


# ─────────────────────────────────────────────────────────────────────────────
# ROUTING FUNCTIONS
# Must return a string matching a node name or the END sentinel.
# ─────────────────────────────────────────────────────────────────────────────

MAX_RETRIES = 2


def route_entry(state: PipelineState) -> str:
    """Route follow-ups (with cached manifest) to plan, else to preprocess."""
    if state.get("is_followup") and (state.get("manifest") or state.get("manifests")):
        return "plan"
    return "preprocess"


def after_preprocess(state: PipelineState) -> str:
    if state.get("error"):
        return END
    return "plan"


def after_plan(state: PipelineState) -> str:
    if state.get("error"):
        return END
    if state.get("is_followup"):
        return "analyze"          # skip human_review for follow-ups
    return "human_review"


def after_human_review(state: PipelineState) -> str:
    if state.get("approved") is True:
        return "analyze"
    return END


_FORECAST_KEYWORDS = {"forecast", "predict", "projection", "trend", "future", "outlook", "extrapolat"}

def _question_wants_forecast(question: str) -> bool:
    """Check if the user's question is asking for forecasting."""
    q = question.lower()
    return any(kw in q for kw in _FORECAST_KEYWORDS)


def after_analyze(state: PipelineState) -> str:
    if not state.get("error"):
        if state.get("is_followup") and not _question_wants_forecast(state.get("question", "")):
            return "graph_gen"    # skip forecast for follow-ups unless they ask for it
        return "forecast"
    # Route back to preprocess for retry (up to MAX_RETRIES)
    if state.get("retry_count", 0) < MAX_RETRIES:
        return "retry_bump"
    return END


def after_graph_gen(state: PipelineState) -> str:
    """Route follow-ups to explanation; initial runs end and summarize outside the graph."""
    if state.get("is_followup"):
        return "followup_explain"
    return END


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH ASSEMBLY
# ─────────────────────────────────────────────────────────────────────────────

def build_pipeline():
    builder = StateGraph(PipelineState)

    builder.add_node("entry_router",     entry_router_node)
    builder.add_node("preprocess",       preprocess_node)
    builder.add_node("plan",             plan_node)
    builder.add_node("human_review",     human_review_node)
    builder.add_node("analyze",          analyze_node)
    builder.add_node("retry_bump",       retry_bump_node)
    builder.add_node("forecast",         forecast_node)
    builder.add_node("graph_gen",        graph_gen_node)
    builder.add_node("summarize",        summarize_node)
    builder.add_node("followup_explain", followup_explain_node)

    builder.set_entry_point("entry_router")

    # Entry: follow-ups (with cached manifest) skip preprocess
    builder.add_conditional_edges(
        "entry_router", route_entry,
        {"preprocess": "preprocess", "plan": "plan"},
    )

    builder.add_conditional_edges(
        "preprocess", after_preprocess,
        {"plan": "plan", END: END},
    )

    # Plan: follow-ups skip human_review
    builder.add_conditional_edges(
        "plan", after_plan,
        {"human_review": "human_review", "analyze": "analyze", END: END},
    )

    builder.add_conditional_edges(
        "human_review", after_human_review,
        {"analyze": "analyze", END: END},
    )

    # Analyze: follow-ups skip forecast → go straight to graph_gen
    builder.add_conditional_edges(
        "analyze", after_analyze,
        {"forecast": "forecast", "graph_gen": "graph_gen", "retry_bump": "retry_bump", END: END},
    )

    builder.add_edge("retry_bump", "preprocess")
    builder.add_edge("forecast",   "graph_gen")

    # Graph gen: follow-ups → followup_explain, initial → summarize
    builder.add_conditional_edges(
        "graph_gen", after_graph_gen,
        {"followup_explain": "followup_explain", END: END},
    )

    builder.add_edge("summarize",        END)
    builder.add_edge("followup_explain", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# Singleton compiled graph — imported by backend.py
pipeline = build_pipeline()
