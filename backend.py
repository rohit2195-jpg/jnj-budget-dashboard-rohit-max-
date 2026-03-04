import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from langgraph.types import Command

from pipeline.graph import pipeline

app = Flask(__name__)
CORS(app)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/analyze/start
#
# Runs preprocess → plan → human_review (interrupt).
# Returns the analysis plan to the frontend for user approval.
#
# Request body:  { "question": "...", "filepath": "..." }
# Response:
#   pending_approval: { "status": "pending_approval", "thread_id": "...", "plan": {...} }
#   error:            { "status": "error", "error": "..." }
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/analyze/start', methods=['POST'])
def start_analysis():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400

        user_question = data.get('question')
        data_path = data.get('filepath', 'data/US Spending Data/spending_data.json')

        if not user_question:
            return jsonify({"error": "Missing 'question' in request body"}), 400

        if not os.path.exists(data_path):
            return jsonify({"error": f"File not found: '{data_path}'"}), 404

        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "question":    user_question,
            "data_path":   data_path,
            "retry_count": 0,
            "error":       None,
            "approved":    None,
        }

        print(f"[{thread_id[:8]}] Starting pipeline for: {user_question}")

        # Run until interrupt() fires in human_review_node (or until END on error).
        for _ in pipeline.stream(initial_state, config=config):
            pass

        graph_state = pipeline.get_state(config)

        # Check whether the graph is paused at an interrupt
        is_interrupted = any(bool(task.interrupts) for task in graph_state.tasks)

        if is_interrupted:
            # Graph paused at human_review_node — surface plan to frontend
            interrupt_value = graph_state.tasks[0].interrupts[0].value
            plan = interrupt_value.get("plan", graph_state.values.get("plan", {}))
            print(f"[{thread_id[:8]}] Graph paused for human review.")
            return jsonify({
                "status":    "pending_approval",
                "thread_id": thread_id,
                "plan":      plan,
            }), 200

        # Graph ended early (preprocess or plan failed)
        values = graph_state.values
        if values.get("error"):
            return jsonify({"status": "error", "error": values["error"]}), 500

        # Unexpected: graph completed without interrupt
        return jsonify({"status": "error", "error": "Unexpected pipeline termination."}), 500

    except Exception as exc:
        print(f"Error in /api/analyze/start: {exc}")
        return jsonify({"error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/analyze/resume
#
# Resumes the paused pipeline after human approves/rejects the plan.
# Runs analyze → graph_gen → summarize.
#
# Request body:  { "thread_id": "...", "approved": true/false }
# Response:
#   approved:   { "status": "complete", "success": true, "summary": "...", "graphs": {...} }
#   rejected:   { "status": "rejected" }
#   error:      { "status": "error", "error": "..." }
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/analyze/resume', methods=['POST'])
def resume_analysis():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400

        thread_id = data.get('thread_id')
        approved  = data.get('approved')

        if not thread_id:
            return jsonify({"error": "Missing 'thread_id'"}), 400
        if approved is None:
            return jsonify({"error": "Missing 'approved' field"}), 400

        config = {"configurable": {"thread_id": thread_id}}

        # Verify the thread is actually paused waiting for approval
        graph_state = pipeline.get_state(config)
        is_interrupted = any(bool(task.interrupts) for task in graph_state.tasks)
        if not is_interrupted:
            return jsonify({"error": "No pending approval found for this thread_id."}), 400

        print(f"[{thread_id[:8]}] Resuming with approved={approved}")

        # Resume: Command(resume=approved) makes interrupt() return `approved`
        # inside human_review_node, which stores it as state["approved"].
        for _ in pipeline.stream(Command(resume=approved), config=config):
            pass

        final_values = pipeline.get_state(config).values

        if not approved:
            return jsonify({"status": "rejected"}), 200

        if final_values.get("error") and not final_values.get("summary"):
            return jsonify({"status": "error", "error": final_values["error"]}), 500

        return jsonify({
            "status":          "complete",
            "success":         True,
            "summary":         final_values.get("summary", ""),
            "graphs":          final_values.get("graph_data", {"charts": []}),
            "forecast_output": final_values.get("forecast_output", {"forecasts": []}),
        }), 200

    except Exception as exc:
        print(f"Error in /api/analyze/resume: {exc}")
        return jsonify({"error": str(exc)}), 500


if __name__ == '__main__':
    # use_reloader=False prevents a child-process fork that would lose the
    # in-memory MemorySaver state between /start and /resume calls.
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)
