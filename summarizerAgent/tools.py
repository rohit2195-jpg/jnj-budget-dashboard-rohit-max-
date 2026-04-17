from langchain.tools import tool
import os


def _resolve_report_path(filename: str) -> str:
    """Normalize report targets so callers can pass a bare filename or a reports/ path."""
    cleaned = (filename or "").strip()
    if not cleaned:
        cleaned = "analysis_report.md"

    if os.path.isabs(cleaned):
        return cleaned

    normalized = os.path.normpath(cleaned)
    if normalized == "reports" or normalized.endswith(os.sep):
        normalized = os.path.join(normalized, "analysis_report.md")

    if normalized == ".":
        normalized = "analysis_report.md"

    if normalized == "reports" or normalized.startswith(f"reports{os.sep}"):
        return normalized

    return os.path.join("reports", normalized)


@tool
def save_analysis_to_txt(content: str, filename: str) -> str:
    """
    Saves the LLM's analysis to a text file.
    Provide the full analysis content as the 'content' argument.
    Only used if user asks for a report in the form of a file
    """
    print("LLM is saving response to file")
    filepath = _resolve_report_path(filename)
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Analysis successfully saved to {filepath}"
    except Exception as e:
        return f"Error saving file: {str(e)}"
