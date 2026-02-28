from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from pipeline.state import PipelineState, serialize_analysis_output

# Existing agent imports
from pre_processing.processing_agent import callPreProcessAgent
from plannerAgent.planner_agent import create_analysis_plan
from agent_tools.agent import callAgent
from graphAgent.graphAgent import create_graph
from summarizerAgent.summarizer_agent import summarize_results


# ─────────────────────────────────────────────────────────────────────────────
# NODES
# Each node receives the full PipelineState and returns a partial dict of only
# the keys it changed. LangGraph merges partial updates into the state.
# ─────────────────────────────────────────────────────────────────────────────

def preprocess_node(state: PipelineState) -> dict:
    """
    Run callPreProcessAgent.
    Success → {"manifest": <dict>}
    Failure → {"error": <str>}
    """
    try:
        manifest = callPreProcessAgent(state["data_path"])
        if manifest.get("status") == "error":
            return {"error": f"Preprocessing failed: {manifest.get('error', 'unknown')}"}
        return {"manifest": manifest, "error": None}
    except Exception as exc:
        return {"error": f"Preprocessing exception: {exc}"}


def plan_node(state: PipelineState) -> dict:
    """
    Run create_analysis_plan with question + manifest.
    Success → {"plan": <dict>}
    Failure → {"error": <str>}
    """
    try:
        plan = create_analysis_plan(state["question"], state["manifest"])
        if not plan.get("analyses"):
            return {"error": "Planner returned an empty plan."}
        return {"plan": plan, "error": None}
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
        output = callAgent(state["question"], state["manifest"], state["plan"])
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
        return {"analysis_output": output, "error": None}
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


def graph_gen_node(state: PipelineState) -> dict:
    """
    Run create_graph.  Failure is non-fatal — summarize still runs.
    """
    try:
        serialized = serialize_analysis_output(state.get("analysis_output"))
        graph_data = create_graph(state["question"], serialized)
        return {"graph_data": graph_data}
    except Exception as exc:
        return {"graph_data": {"charts": []}, "error": f"Graph generation exception: {exc}"}


def summarize_node(state: PipelineState) -> dict:
    """
    Run summarize_results.
    """
    try:
        serialized = serialize_analysis_output(state.get("analysis_output"))
        summary = summarize_results(state["question"], serialized, "")
        return {"summary": str(summary)}
    except Exception as exc:
        return {"error": f"Summarization exception: {exc}"}


# ─────────────────────────────────────────────────────────────────────────────
# ROUTING FUNCTIONS
# Must return a string matching a node name or the END sentinel.
# ─────────────────────────────────────────────────────────────────────────────

MAX_RETRIES = 2


def after_preprocess(state: PipelineState) -> str:
    if state.get("error"):
        return END
    return "plan"


def after_plan(state: PipelineState) -> str:
    if state.get("error"):
        return END
    return "human_review"


def after_human_review(state: PipelineState) -> str:
    if state.get("approved") is True:
        return "analyze"
    return END


def after_analyze(state: PipelineState) -> str:
    if not state.get("error"):
        return "graph_gen"
    # Route back to preprocess for retry (up to MAX_RETRIES)
    if state.get("retry_count", 0) < MAX_RETRIES:
        return "retry_bump"
    return END


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH ASSEMBLY
# ─────────────────────────────────────────────────────────────────────────────

def build_pipeline():
    builder = StateGraph(PipelineState)

    builder.add_node("preprocess",    preprocess_node)
    builder.add_node("plan",          plan_node)
    builder.add_node("human_review",  human_review_node)
    builder.add_node("analyze",       analyze_node)
    builder.add_node("retry_bump",    retry_bump_node)
    builder.add_node("graph_gen",     graph_gen_node)
    builder.add_node("summarize",     summarize_node)

    builder.set_entry_point("preprocess")

    builder.add_conditional_edges(
        "preprocess", after_preprocess,
        {"plan": "plan", END: END},
    )
    builder.add_conditional_edges(
        "plan", after_plan,
        {"human_review": "human_review", END: END},
    )
    builder.add_conditional_edges(
        "human_review", after_human_review,
        {"analyze": "analyze", END: END},
    )
    builder.add_conditional_edges(
        "analyze", after_analyze,
        {"graph_gen": "graph_gen", "retry_bump": "retry_bump", END: END},
    )

    builder.add_edge("retry_bump", "preprocess")
    builder.add_edge("graph_gen",  "summarize")
    builder.add_edge("summarize",  END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# Singleton compiled graph — imported by backend.py
pipeline = build_pipeline()
