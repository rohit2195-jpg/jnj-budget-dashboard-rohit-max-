from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
import os
from dotenv import load_dotenv
from summarizerAgent.tools import save_analysis_to_txt
from agent_tools.llm_model import model


load_dotenv()


agent = create_agent(model, tools=[save_analysis_to_txt])


def summarize_results(user_question, analysis_output):

    analysis_output = agent.invoke(
        {"messages": [{"role": "user", 
                       "content": f"""

    The user asked the following question: "{user_question}"

    An analysis of the dataset produced the following results:
    ---
    {analysis_output}
    ---

    Please provide a summary of these results in a clear and understandable way.
    Based on the data, also provide some additional insights or observations that might be interesting to the user.
    Then save your analysis to a file in markdown.

        """
        }]}
    )

    return analysis_output
