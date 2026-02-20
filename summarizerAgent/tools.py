
from langchain.tools import tool
import json
import os

@tool
def save_analysis_to_txt(content: str, filename:str) -> str:
    """
    Saves the LLM's analysis to a text file.
    Provide the full analysis content as the 'content' argument.
    Only used if user asks for a report in the form of a file
    """
    
    print("LLM is saving response to file")
    filepath = os.path.join("reports", filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Analysis successfully saved to {filepath}"
    except Exception as e:
        return f"Error saving file: {str(e)}"
    
