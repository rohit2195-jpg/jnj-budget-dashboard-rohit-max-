from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
import os
from dotenv import load_dotenv
from summarizerAgent.tools import save_analysis_to_txt
from agent_tools.llm_model import model


load_dotenv()


agent = create_agent(model, tools=[save_analysis_to_txt])


def summarize_results(user_question, analysis_output, outputFilePath):

    invoke_result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
    You are a professional data analyst.

    The user asked:
    "{user_question}"

    The dataset analysis produced the following raw results:
    ---
    {analysis_output}
    ---

    Your task:

    1. Write a clear, well-structured markdown report explaining the results.
    2. Include:
    - A concise executive summary
    - A detailed explanation of the findings
    - Additional insights or interesting observations
    - Any notable trends, anomalies, or patterns
    3. Use proper markdown formatting with headings (##, ###), bullet points, and emphasis where appropriate.
    4. The entire output must be valid markdown.

    File Saving Requirements:
    - Save the markdown report to this file path: {outputFilePath}
    - If {outputFilePath} is empty, choose a logical filename such as:
    report_output.md
    - Do NOT describe the saving process.
    - Do NOT output anything outside the markdown report.
    - The exact markdown content written to the file must be returned as your final output.
    - The returned content must match the file content exactly.

    Do not include explanations about what you are doing.
    Only return the markdown report.
    """
                }
            ]
        }
    )

    last_message = invoke_result["messages"][-1]
    content = last_message.content
    if isinstance(content, list):
        return content[0].get("text", "")
    return content
