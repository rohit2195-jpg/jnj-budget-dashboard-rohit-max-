from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
import os
from dotenv import load_dotenv
from agent_tools.tools import get_weather, search, generate_analysis_code_tool, execute_analysis_tool
from agent_tools.llm_model import model


load_dotenv()


agent = create_agent(model, tools=[search, get_weather, generate_analysis_code_tool, execute_analysis_tool])

def get_final_answer(result):
    for msg in reversed(result["messages"]):
        content = msg.get("content")

        if not content:
            continue

        # Gemini often returns structured content
        if isinstance(content, list):
            return content[0].get("text", "")

        # Plain text case
        if isinstance(content, str):
            return content

    return ""

def callAgent(question, data_path):

    analysis_output = agent.invoke(
        {"messages": [{"role": "user", 
                       "content": f"""You are a data anlayst, use your tools availble to best answer the user question by doing data anlysis on the data
            User question: {question}
            Data path: {data_path}
            Hardcode the data path in your analysis , so that I can execute the program inside the agent_tools folder
        """
        }]}
    )

    return analysis_output
