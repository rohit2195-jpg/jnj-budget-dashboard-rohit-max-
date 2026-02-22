from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
import os
from dotenv import load_dotenv
from agent_tools.llm_model import model
from pre_processing.tools import generate_analysis_code, execute_analysis_tool

load_dotenv()


pre_process_agent = create_agent(model, tools=[generate_analysis_code, execute_analysis_tool])


def callPreProcessAgent(data_path):

    analysis_output = pre_process_agent.invoke(
        {"messages": [{"role": "user", 
                       "content": f"""Please pre-process the data by cleaning, transforming, and organizing raw data into a usable format for future analysis and machine learning
            Data path: {data_path}
            Hardcode the data path in your code.
            Output clean dataset inside './pre_processing/processed_data'
            Give the analyst (who will analyse the dataset) an overview of the data, and where the cleaned dataset is located in your output.
            IMPORTANT: Make sure to output the path to the cleaned dataset in your final answer. ex. (pre_processing/processed_data/[file_name_here])
            Do not include cleaning code.
            The generated code must define a function named 'process_data'. This will be the top level or overall function.


            IMPORTANT: After generating code, use the execute_analysis_tool to actually enact your code and clean the dataset please.
            Final step: IMPORTANT: After generating code, use the execute_analysis_tool to actually enact your code and clean the dataset without errors.

            
                            """
        }]}
    )
    last_message = analysis_output["messages"][-1]
    content = last_message.content
    final_output = content[0]["text"]
    return final_output
