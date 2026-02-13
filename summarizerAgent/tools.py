
from langchain.tools import tool


@tool
def save_analysis_to_txt(content: str) -> str:
    """
    Saves the LLM's analysis to a text file.
    Provide the full analysis content as the 'content' argument.
    """
    filename = 'report.md'
    print("LLM is saving response to file")
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Analysis successfully saved to {filename}"
    except Exception as e:
        return f"Error saving file: {str(e)}"