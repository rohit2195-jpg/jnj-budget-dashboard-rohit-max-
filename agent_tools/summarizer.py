
import os
from google import genai
from dotenv import load_dotenv

def summarize_results(user_question, analysis_output):
    """
    Uses Gemini to summarize the analysis results and provide insights.
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    MODEL_ID = os.getenv("MODEL_ID")

    if not api_key:
        return "Error: GEMINI_API_KEY not found. Please set it in a .env file."

    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    The user asked the following question: "{user_question}"

    An analysis of the dataset produced the following results:
    ---
    {analysis_output}
    ---

    Please provide a summary of these results in a clear and understandable way.
    Based on the data, also provide some additional insights or observations that might be interesting to the user.
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"An error occurred with the LLM: {e}"
