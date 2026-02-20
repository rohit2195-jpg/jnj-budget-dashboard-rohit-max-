from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
import os
from dotenv import load_dotenv
from agent_tools.tools import  generate_analysis_code_tool, execute_analysis_tool
from agent_tools.llm_model import model


load_dotenv()


agent = create_agent(model, tools=[generate_analysis_code_tool, execute_analysis_tool])


def callAgent(question, pre_process_output):

    analysis_output = agent.invoke(
        {"messages": [{"role": "user", 
                       "content": f"""You are a data anlayst, use your tools availble to best answer the user question by doing data anlysis on the data
            User question: {question}
            Pre_processing_output: {pre_process_output}
            The data path will be found in the pre_processing_output
            Hardcode the data path in your analysis , so that I can execute the program inside the agent_tools folder.

            The generated code must define a function named 'analyze_spending_data'. This will be the top level or overall function.


           """
        }]}
    )

    last_message = analysis_output["messages"][-1]
    content = last_message.content

    print("TYPE:", type(content))  # should say list

    final_output = content[0]["text"]

    return final_output
