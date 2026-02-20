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
    Then save your analysis to a file in markdown to this file path: {outputFilePath}. If empty, give it any name that best suits the query. eg. (report_output.md)


        """
        }]}
    )

    last_message = analysis_output["messages"][-1]
    content = last_message.content
    final_output = content[0]["text"]

    return final_output
