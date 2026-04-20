import json
import os
import re
import tempfile
import threading
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from langgraph.types import Command
from werkzeug.utils import secure_filename

from pipeline.graph import (
    pipeline,
    analyze_node,
    forecast_node,
    graph_gen_node,
    followup_explain_node,
    _question_wants_forecast,
    MAX_RETRIES,
)
from pipeline.state import serialize_analysis_output
from summarizerAgent.summarizer_agent import summarize_results
from agent_tools.llm_model import model

app = Flask(__name__)
MAX_UPLOAD_BYTES = 250 * 1024 * 1024

app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_BYTES  # 250 MB upload limit
DEFAULT_CORS_ORIGINS = ['http://localhost:5173', 'http://127.0.0.1:5173']
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                origin.strip()
                for origin in os.getenv('CORS_ORIGINS', '').split(',')
                if origin.strip()
            ] or DEFAULT_CORS_ORIGINS
        }
    },
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
SESSIONS_FILE = os.path.join(REPORTS_DIR, 'followup_sessions.json')
DATASET_ALIASES_FILE = os.path.join(REPORTS_DIR, 'dataset_aliases.json')
ALLOWED_EXTENSIONS = {'.csv', '.json'}
MAX_FILES_PER_ANALYSIS = 10
SESSION_LOCK = threading.Lock()
DATASET_ALIAS_LOCK = threading.Lock()
CONSUMED_APPROVAL_THREADS = set()


def _resolve_data_path(requested_path):
    """Resolve a requested file or folder path and keep it inside data/."""
    if not requested_path or not isinstance(requested_path, str):
        raise ValueError("Invalid dataset path.")

    normalized = requested_path.replace('\\', '/').strip()
    if normalized.startswith('data/'):
        normalized = normalized[5:]
    normalized = normalized.strip('/')

    abs_path = os.path.abspath(os.path.join(DATA_DIR, normalized))
    data_root = os.path.abspath(DATA_DIR)
    if os.path.commonpath([data_root, abs_path]) != data_root:
        raise ValueError("Dataset path must stay inside the data directory.")

    return abs_path


def _to_repo_relative(abs_path):
    return os.path.relpath(abs_path, BASE_DIR)


def _strip_dataset_extension(name):
    if not name:
        return ""
    lowered = name.lower()
    for ext in sorted(ALLOWED_EXTENSIONS, key=len, reverse=True):
        if lowered.endswith(ext):
            return name[:-len(ext)]
    return name


def _derive_dataset_name(dataset_path):
    if not dataset_path:
        return "Unknown dataset"
    normalized = dataset_path.replace('\\', '/').rstrip('/')
    leaf = normalized.split('/')[-1] if normalized else dataset_path
    leaf = _strip_dataset_extension(leaf)
    return leaf or "Unknown dataset"


def _friendly_dataset_alias(dataset_name):
    cleaned = re.sub(r'[_-]+', ' ', dataset_name or '')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if not cleaned:
        return None
    parts = []
    for token in cleaned.split(' '):
        if token.isupper() and len(token) <= 4:
            parts.append(token)
        else:
            parts.append(token.capitalize())
    alias = ' '.join(parts)
    return alias[:80] if alias else None


def _load_dataset_aliases():
    if not os.path.exists(DATASET_ALIASES_FILE):
        return {}

    try:
        with open(DATASET_ALIASES_FILE, 'r', encoding='utf-8') as fh:
            raw = json.load(fh)
        if not isinstance(raw, dict):
            return {}
        return {
            str(path): str(alias).strip()
            for path, alias in raw.items()
            if isinstance(path, str) and isinstance(alias, str) and str(alias).strip()
        }
    except Exception as exc:
        print(f"Warning: failed to load dataset aliases: {exc}")
        return {}


def _save_dataset_aliases():
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix='dataset_aliases_', suffix='.json', dir=REPORTS_DIR)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                json.dump(dataset_aliases, fh, indent=2)
            os.replace(temp_path, DATASET_ALIASES_FILE)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    except Exception as exc:
        print(f"Warning: failed to persist dataset aliases: {exc}")


def _generate_dataset_alias(dataset_name, manifests=None):
    friendly = _friendly_dataset_alias(dataset_name)
    manifest_lines = []
    for manifest in (manifests or [])[:3]:
        if not isinstance(manifest, dict):
            continue
        columns = [str(col) for col in (manifest.get("columns") or [])[:8]]
        row_count = manifest.get("row_count")
        summary = str(manifest.get("summary") or "").strip()
        line = f"- file: {manifest.get('source_file') or manifest.get('data_path') or dataset_name}"
        if row_count is not None:
            line += f"; rows: {row_count}"
        if columns:
            line += f"; columns: {', '.join(columns)}"
        if summary:
            line += f"; summary: {summary[:220]}"
        manifest_lines.append(line)

    prompt = (
        "Create a short, human-friendly dataset alias.\n"
        "Rules:\n"
        "- Return only the alias text\n"
        "- 2 to 6 words\n"
        "- No quotes, no colon, no markdown\n"
        "- Prefer descriptive business language over file naming\n"
        "- Reuse well-known acronyms when helpful\n"
        f"- Base dataset name: {dataset_name}\n"
    )
    if manifest_lines:
        prompt += "Dataset details:\n" + "\n".join(manifest_lines) + "\n"

    try:
        response = model.invoke(prompt)
        raw = response.content if hasattr(response, "content") else getattr(response, "text", "")
        if isinstance(raw, list):
            raw = raw[0].get("text", "") if raw else ""
        alias = re.sub(r'\s+', ' ', str(raw).strip()).strip('"\'')
        alias = alias[:80].strip()
        if alias:
            return alias
    except Exception as exc:
        print(f"Warning: failed to generate dataset alias for '{dataset_name}': {exc}")

    return friendly


def _get_dataset_alias(dataset_path, dataset_name, manifests=None):
    if not dataset_path:
        return None

    with DATASET_ALIAS_LOCK:
        cached = dataset_aliases.get(dataset_path)
        if cached:
            return cached

    alias = _generate_dataset_alias(dataset_name, manifests=manifests)
    if not alias:
        return None

    with DATASET_ALIAS_LOCK:
        existing = dataset_aliases.get(dataset_path)
        if existing:
            return existing
        dataset_aliases[dataset_path] = alias
        _save_dataset_aliases()
    return alias


def _derive_dataset_path(requested_dataset_path, data_paths):
    if requested_dataset_path:
        normalized = requested_dataset_path.replace('\\', '/')
        return normalized if not normalized.endswith('/') else normalized.rstrip('/') + '/'
    if len(data_paths) == 1:
        return data_paths[0]

    common_path = os.path.commonpath([os.path.join(BASE_DIR, dp) for dp in data_paths])
    if os.path.isfile(common_path):
        common_path = os.path.dirname(common_path)
    return _to_repo_relative(common_path).replace('\\', '/').rstrip('/') + '/'


def _session_source_paths(payload):
    if not isinstance(payload, dict):
        return []

    source_paths = []
    for key in ("data_paths",):
        values = payload.get(key)
        if isinstance(values, list):
            source_paths.extend(str(value) for value in values if isinstance(value, str) and value)

    for manifest in (payload.get("manifests") or []):
        if isinstance(manifest, dict):
            source = manifest.get("source_file") or manifest.get("data_path")
            if isinstance(source, str) and source:
                source_paths.append(source)

    manifest = payload.get("manifest")
    if isinstance(manifest, dict):
        source = manifest.get("source_file") or manifest.get("data_path")
        if isinstance(source, str) and source:
            source_paths.append(source)

    data_path = payload.get("data_path")
    if isinstance(data_path, str) and data_path:
        source_paths.append(data_path)

    deduped = []
    seen = set()
    for path in source_paths:
        normalized = path.replace('\\', '/')
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _infer_dataset_path_from_session_payload(payload):
    if not isinstance(payload, dict):
        return ""

    explicit = payload.get("dataset_path")
    if isinstance(explicit, str) and explicit:
        normalized = explicit.replace('\\', '/')
        return normalized if not normalized.endswith('/') else normalized.rstrip('/') + '/'

    source_paths = _session_source_paths(payload)
    if not source_paths:
        return ""
    if len(source_paths) == 1:
        return source_paths[0]

    abs_paths = []
    for path in source_paths:
        try:
            abs_paths.append(_resolve_data_path(path))
        except ValueError:
            continue

    if len(abs_paths) < 2:
        common_rel = os.path.commonpath(source_paths)
        if common_rel and common_rel != '.':
            if any(path != common_rel for path in source_paths):
                if os.path.splitext(common_rel)[1].lower() in ALLOWED_EXTENSIONS:
                    common_rel = os.path.dirname(common_rel)
                return common_rel.replace('\\', '/').rstrip('/') + '/'
            return common_rel.replace('\\', '/')
        return source_paths[0]

    common_path = os.path.commonpath(abs_paths)
    if os.path.isfile(common_path):
        common_path = os.path.dirname(common_path)
    return _to_repo_relative(common_path).replace('\\', '/').rstrip('/') + '/'


def _get_session_dataset_metadata(payload, ensure_alias=False):
    dataset_path = _infer_dataset_path_from_session_payload(payload)
    dataset_name = payload.get("dataset_name") or _derive_dataset_name(dataset_path)
    dataset_alias = payload.get("dataset_alias")
    manifests = payload.get("manifests")
    if not manifests and payload.get("manifest"):
        manifests = [payload.get("manifest")]
    if ensure_alias and dataset_path and not dataset_alias:
        dataset_alias = _get_dataset_alias(dataset_path, dataset_name, manifests=manifests)
    return {
        "dataset_path": dataset_path or None,
        "dataset_name": dataset_name or None,
        "dataset_alias": dataset_alias or None,
    }


def _normalize_session(payload):
    """Keep persisted session payloads backward-compatible and minimal."""
    if not isinstance(payload, dict):
        return None
    # Backward compat: build data_paths/manifests from single-file fields if missing
    data_path = payload.get("data_path", "")
    data_paths = payload.get("data_paths") or ([data_path] if data_path else [])
    manifest = payload.get("manifest")
    manifests = payload.get("manifests") or ([manifest] if manifest else [])
    dataset_meta = _get_session_dataset_metadata(payload, ensure_alias=False)
    return {
        "manifest": manifest,
        "manifests": manifests,
        "data_path": data_path,
        "data_paths": data_paths,
        "dataset_path": dataset_meta["dataset_path"] or data_path,
        "dataset_name": dataset_meta["dataset_name"] or _derive_dataset_name(dataset_meta["dataset_path"] or data_path),
        "dataset_alias": dataset_meta["dataset_alias"],
        "conversation_history": payload.get("conversation_history") or [],
        "all_chart_ids": payload.get("all_chart_ids") or [],
    }


def _load_sessions():
    """Load follow-up sessions from disk so saved chats survive backend restarts."""
    if not os.path.exists(SESSIONS_FILE):
        return {}

    try:
        with open(SESSIONS_FILE, 'r', encoding='utf-8') as fh:
            raw = json.load(fh)
        if not isinstance(raw, dict):
            return {}
        return {
            session_id: normalized
            for session_id, payload in raw.items()
            if (normalized := _normalize_session(payload)) is not None
        }
    except Exception as exc:
        print(f"Warning: failed to load persisted follow-up sessions: {exc}")
        return {}


def _save_sessions():
    """Persist follow-up sessions so localStorage conversations keep working."""
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix='followup_sessions_', suffix='.json', dir=REPORTS_DIR)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                json.dump(sessions, fh, indent=2)
            os.replace(temp_path, SESSIONS_FILE)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    except Exception as exc:
        print(f"Warning: failed to persist follow-up sessions: {exc}")


def _push_warning(state, message):
    warnings = list(state.get("warnings") or [])
    warnings.append(message)
    state["warnings"] = warnings


def _dedupe_charts(charts, prior_chart_ids=None):
    seen = set(prior_chart_ids or [])
    deduped = []
    for idx, chart in enumerate(charts or []):
        if not isinstance(chart, dict):
            continue
        chart_id = str(chart.get("id") or f"chart-{idx + 1}")
        if chart_id in seen:
            original_id = chart_id
            suffix = 2
            while f"{original_id}-{suffix}" in seen:
                suffix += 1
            chart = dict(chart)
            chart_id = f"{original_id}-{suffix}"
            chart["id"] = chart_id
        seen.add(chart_id)
        deduped.append(chart)
    return deduped


def _run_postplan_nodes(state):
    """
    Execute the post-plan pipeline directly in Python instead of through LangGraph.

    We still use LangGraph for the pause/resume approval boundary, but after approval
    we avoid further checkpoint writes because msgpack serialization has proven brittle
    around LLM/tool outputs.
    """
    working = dict(state)

    working["warnings"] = list(working.get("warnings") or [])

    for _ in range(MAX_RETRIES + 1):
        analysis_update = analyze_node(working)
        working.update(analysis_update)
        if not working.get("error"):
            break
        if working.get("retry_count", 0) >= MAX_RETRIES:
            return working
        working["retry_count"] = working.get("retry_count", 0) + 1
        working["analysis_output"] = None
        working["error"] = None

    if working.get("error"):
        return working

    if not working.get("is_followup") or _question_wants_forecast(working.get("question", "")):
        forecast_update = forecast_node(working)
        working.update(forecast_update)
        if working.get("error"):
            _push_warning(working, working["error"])
            working["error"] = None

    graph_update = graph_gen_node(working)
    working.update(graph_update)
    if working.get("error") and not working.get("graph_data"):
        return working
    if working.get("error"):
        _push_warning(working, working["error"])
        working["error"] = None

    graph_data = working.get("graph_data") or {"charts": []}
    deduped_charts = _dedupe_charts(graph_data.get("charts", []), working.get("prior_charts"))
    if len(deduped_charts) != len(graph_data.get("charts", [])):
        _push_warning(working, "Duplicate chart ids were remapped to keep dashboard charts unique.")
    working["graph_data"] = {**graph_data, "charts": deduped_charts}

    if working.get("is_followup"):
        explain_update = followup_explain_node(working)
        working.update(explain_update)

    return working


# Follow-up session store.
# Maps session_id -> {manifest, data_path, conversation_history, all_chart_ids}
sessions = _load_sessions()
dataset_aliases = _load_dataset_aliases()


@app.errorhandler(413)
def request_entity_too_large(_):
    return jsonify({'error': 'File too large. Maximum size is 250 MB.'}), 413


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/datasets
#
# Lists available datasets (CSV/JSON) under the data/ directory.
# Response: { "datasets": [{ "name": "...", "path": "...", "size": ... }, ...] }
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/datasets', methods=['GET'])
def list_datasets():
    datasets = []
    folder_files = {}  # track files per subfolder for folder entries

    for root, dirs, files in os.walk(DATA_DIR):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for fname in files:
            if fname.startswith('.'):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            abs_path = os.path.join(root, fname)
            rel_path = os.path.relpath(abs_path, os.path.dirname(DATA_DIR))
            display_name = os.path.relpath(abs_path, DATA_DIR)

            # Track subfolder membership
            parent = os.path.relpath(root, DATA_DIR)
            if parent != '.':
                folder_files.setdefault(parent, []).append(rel_path)
            else:
                # Only list top-level files individually
                datasets.append({
                    'name': display_name,
                    'display_name': _derive_dataset_name(rel_path),
                    'path': rel_path,
                    'size': os.path.getsize(abs_path),
                    'type': 'file',
                })

    # Add folder-level entries for subdirectories with data files
    for folder_name, file_list in folder_files.items():
        if len(file_list) >= 1:
            folder_rel = os.path.relpath(os.path.join(DATA_DIR, folder_name),
                                         os.path.dirname(DATA_DIR))
            datasets.append({
                'name': folder_name + '/',
                'display_name': _derive_dataset_name(folder_rel + '/'),
                'path': folder_rel + '/',
                'type': 'folder',
                'file_count': len(file_list),
                'files': sorted(file_list),
            })

    datasets.sort(key=lambda d: d['name'].lower())
    return jsonify({'datasets': datasets}), 200


@app.route('/api/sessions/<session_id>/dataset', methods=['GET'])
def session_dataset_metadata(session_id):
    with SESSION_LOCK:
        session = sessions.get(session_id)
        if session is None:
            return jsonify({'error': 'Session not found'}), 404

        dataset_meta = _get_session_dataset_metadata(session, ensure_alias=True)
        changed = any(session.get(key) != value for key, value in dataset_meta.items())
        if changed:
            session.update(dataset_meta)
            _save_sessions()

    return jsonify({
        'session_id': session_id,
        **dataset_meta,
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/upload
#
# Upload a CSV or JSON file to the data/ directory.
# Accepts multipart form data with a 'file' field.
# Response: { "path": "data/filename.csv" }
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/upload', methods=['POST'])
def upload_dataset():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(DATA_DIR, filename)
    file.save(save_path)

    rel_path = os.path.relpath(save_path, os.path.dirname(DATA_DIR))
    return jsonify({'path': rel_path}), 200


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/upload-folder
#
# Upload multiple CSV/JSON files into a named subfolder under data/.
# Accepts multipart form data with multiple 'files' fields and optional 'folder_name'.
# Response: { "folder_path": "data/my_folder/", "files": ["data/my_folder/a.csv", ...] }
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/upload-folder', methods=['POST'])
def upload_folder():
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files provided'}), 400

    # Filter to allowed extensions
    valid_files = []
    for f in files:
        if not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1].lower()
        if ext in ALLOWED_EXTENSIONS:
            valid_files.append(f)

    if not valid_files:
        return jsonify({'error': 'No valid CSV/JSON files found'}), 400

    if len(valid_files) > MAX_FILES_PER_ANALYSIS:
        return jsonify({'error': f'Too many files. Maximum is {MAX_FILES_PER_ANALYSIS}.'}), 400

    folder_name = request.form.get('folder_name', '').strip()
    if not folder_name:
        folder_name = f"upload_{uuid.uuid4().hex[:8]}"
    folder_name = secure_filename(folder_name)
    if not folder_name:
        folder_name = f"upload_{uuid.uuid4().hex[:8]}"

    folder_path = os.path.join(DATA_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    saved_paths = []
    for f in valid_files:
        filename = secure_filename(f.filename)
        save_path = os.path.join(folder_path, filename)
        f.save(save_path)
        saved_paths.append(os.path.relpath(save_path, os.path.dirname(DATA_DIR)))

    folder_rel = os.path.relpath(folder_path, os.path.dirname(DATA_DIR))
    return jsonify({
        'folder_path': folder_rel + '/',
        'files': sorted(saved_paths),
    }), 200


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
        filepaths = data.get('filepaths')  # list of paths (multi-file)
        filepath = data.get('filepath', 'data/census/Dataset.csv')  # single path (backward compat)
        requested_dataset_path = data.get('dataset_path')

        if not user_question:
            return jsonify({"error": "Missing 'question' in request body"}), 400

        # Build data_paths list
        if filepaths and isinstance(filepaths, list):
            data_paths = []
            for requested_path in filepaths:
                abs_path = _resolve_data_path(requested_path)
                ext = os.path.splitext(abs_path)[1].lower()
                if ext not in ALLOWED_EXTENSIONS or not os.path.isfile(abs_path):
                    return jsonify({"error": f"Invalid dataset file: '{requested_path}'"}), 400
                data_paths.append(_to_repo_relative(abs_path))
        elif filepath:
            abs_path = _resolve_data_path(filepath)
            if os.path.isdir(abs_path):
                # Directory path: glob for CSV/JSON files inside
                data_paths = sorted(
                    _to_repo_relative(os.path.join(root, filename))
                    for root, _, files in os.walk(abs_path)
                    for filename in files
                    if os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS
                    and not filename.startswith('.')
                )
                if not data_paths:
                    return jsonify({"error": f"No CSV/JSON files found in '{filepath}'"}), 400
            else:
                ext = os.path.splitext(abs_path)[1].lower()
                if ext not in ALLOWED_EXTENSIONS or not os.path.isfile(abs_path):
                    return jsonify({"error": f"Invalid dataset file: '{filepath}'"}), 400
                data_paths = [_to_repo_relative(abs_path)]
        else:
            return jsonify({"error": "Missing dataset path"}), 400

        if len(data_paths) > MAX_FILES_PER_ANALYSIS:
            return jsonify({"error": f"Too many files ({len(data_paths)}). Maximum is {MAX_FILES_PER_ANALYSIS}."}), 400

        # Validate all paths exist
        for dp in data_paths:
            if not os.path.exists(os.path.join(BASE_DIR, dp)):
                return jsonify({"error": f"File not found: '{dp}'"}), 404

        dataset_path = _derive_dataset_path(requested_dataset_path, data_paths)
        dataset_name = _derive_dataset_name(dataset_path)

        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "question":    user_question,
            "data_path":   data_paths[0],
            "data_paths":  data_paths,
            "dataset_path": dataset_path,
            "dataset_name": dataset_name,
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

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
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
        if thread_id in CONSUMED_APPROVAL_THREADS:
            return jsonify({"error": "This approval token has already been used."}), 400

        print(f"[{thread_id[:8]}] Resuming with approved={approved}")

        if not approved:
            CONSUMED_APPROVAL_THREADS.add(thread_id)
            return jsonify({"status": "rejected"}), 200

        # Resume only the approval checkpoint, then run the remaining nodes
        # directly in Python to avoid msgpack serialization failures from
        # downstream LLM/tool outputs.
        base_values = dict(graph_state.values)
        base_values["approved"] = True
        base_values["error"] = None
        final_values = _run_postplan_nodes(base_values)
        CONSUMED_APPROVAL_THREADS.add(thread_id)

        if final_values.get("error") and not final_values.get("summary"):
            return jsonify({"status": "error", "error": final_values["error"]}), 500

        # Generate the markdown report outside LangGraph checkpointing.
        # This avoids resume failures when tool/LLM internals produce objects
        # that the checkpointer cannot msgpack-serialize.
        summary_text = final_values.get("summary", "")
        if not summary_text:
            try:
                summary_text = summarize_results(
                    final_values.get("question", ""),
                    serialize_analysis_output(final_values.get("analysis_output")),
                    "analysis_report.md",
                    final_values.get("forecast_output"),
                )
            except Exception as exc:
                return jsonify({"status": "error", "error": f"Summarization exception: {exc}"}), 500

        dataset_path = final_values.get("dataset_path") or final_values.get("data_path", "")
        dataset_name = final_values.get("dataset_name") or _derive_dataset_name(dataset_path)
        dataset_alias = final_values.get("dataset_alias") or _get_dataset_alias(
            dataset_path,
            dataset_name,
            manifests=final_values.get("manifests"),
        )

        # Create a session for follow-up questions
        session_id = str(uuid.uuid4())
        graph_data = final_values.get("graph_data", {"charts": []})
        original_question = final_values.get("question", "")

        with SESSION_LOCK:
            sessions[session_id] = {
                "manifest":             final_values.get("manifest"),
                "manifests":            final_values.get("manifests"),
                "data_path":            final_values.get("data_path", ""),
                "data_paths":           final_values.get("data_paths"),
                "dataset_path":         dataset_path,
                "dataset_name":         dataset_name,
                "dataset_alias":        dataset_alias,
                "conversation_history": [
                    {
                        "question":        original_question,
                        "summary_snippet": summary_text[:300],
                    }
                ],
                "all_chart_ids": [c.get("id", "") for c in graph_data.get("charts", [])],
            }
            _save_sessions()

        return jsonify({
            "status":          "complete",
            "success":         True,
            "session_id":      session_id,
            "dataset_path":    dataset_path,
            "dataset_name":    dataset_name,
            "dataset_alias":   dataset_alias,
            "summary":         summary_text,
            "graphs":          graph_data,
            "forecast_output": final_values.get("forecast_output", {"forecasts": []}),
            "warnings":        final_values.get("warnings", []),
        }), 200

    except Exception as exc:
        print(f"Error in /api/analyze/resume: {exc}")
        return jsonify({"error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/analyze/followup
#
# Runs a lightweight follow-up analysis on the same dataset.
# Reuses cached manifest, skips preprocessing / human review / forecast.
#
# Request body:  { "question": "...", "session_id": "..." }
# Response:
#   complete:  { "status": "complete", "new_charts": [...], "explanation": "..." }
#   error:     { "status": "error", "error": "..." }
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/analyze/followup', methods=['POST'])
def followup_analysis():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400

        user_question = data.get('question')
        session_id = data.get('session_id')

        if not user_question:
            return jsonify({"error": "Missing 'question'"}), 400
        if not session_id or session_id not in sessions:
            return jsonify({"error": "Invalid or expired session_id"}), 400

        with SESSION_LOCK:
            session = dict(sessions[session_id])

        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        followup_state = {
            "question":             user_question,
            "data_path":            session["data_path"],
            "data_paths":           session.get("data_paths") or [session["data_path"]],
            "dataset_path":         session.get("dataset_path") or session["data_path"],
            "dataset_name":         session.get("dataset_name") or _derive_dataset_name(session.get("dataset_path") or session["data_path"]),
            "dataset_alias":        session.get("dataset_alias"),
            "manifest":             session["manifest"],
            "manifests":            session.get("manifests") or ([session["manifest"]] if session["manifest"] else []),
            "is_followup":          True,
            "conversation_history": session["conversation_history"],
            "prior_charts":         session["all_chart_ids"],
            "retry_count":          0,
            "error":                None,
            "approved":             None,
        }

        print(f"[{thread_id[:8]}] Follow-up for session {session_id[:8]}: {user_question}")

        final_values = _run_postplan_nodes(followup_state)

        if final_values.get("error") and not final_values.get("graph_data"):
            return jsonify({"status": "error", "error": final_values["error"]}), 500

        new_charts = final_values.get("graph_data", {}).get("charts", [])
        explanation = final_values.get("followup_explanation", "")

        # Update session history (cap at 5 entries)
        with SESSION_LOCK:
            live_session = sessions.get(session_id)
            if live_session is None:
                return jsonify({"error": "Invalid or expired session_id"}), 400
            live_session["conversation_history"].append({
                "question":        user_question,
                "summary_snippet": explanation[:300],
            })
            if len(live_session["conversation_history"]) > 5:
                live_session["conversation_history"] = live_session["conversation_history"][-5:]

            live_session["all_chart_ids"].extend(c.get("id", "") for c in new_charts)
            _save_sessions()

        forecast_output = final_values.get("forecast_output", {"forecasts": []})

        return jsonify({
            "status":          "complete",
            "new_charts":      new_charts,
            "explanation":     explanation,
            "forecast_output": forecast_output,
            "warnings":        final_values.get("warnings", []),
        }), 200

    except Exception as exc:
        print(f"Error in /api/analyze/followup: {exc}")
        return jsonify({"error": str(exc)}), 500


if __name__ == '__main__':
    # use_reloader=False prevents a child-process fork that would lose the
    # in-memory MemorySaver state between /start and /resume calls.
    debug_mode = os.getenv('FLASK_DEBUG', '').lower() in {'1', 'true', 'yes'}
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', '5001'))
    app.run(debug=debug_mode, host=host, port=port, use_reloader=False)
