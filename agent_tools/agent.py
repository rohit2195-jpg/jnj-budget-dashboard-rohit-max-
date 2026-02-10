from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
import os
from dotenv import load_dotenv
from tools import get_weather, search, generate_analysis_code_tool, execute_analysis_tool
from llm_model import model


load_dotenv()



messages = [
    (
        "system",
        "You are a helpful assistant that translates English to French. Translate the user sentence.",
    ),
    ("human", "I love programming."),
]



agent = create_agent(model, tools=[search, get_weather, generate_analysis_code_tool, execute_analysis_tool])

result = agent.invoke(
    {"messages": [{"role": "user", "content": "Where is the top 10 places the us is spending money? US dataset located at ../data/US Spending Data/spending_data.json. Can you give me the python output of this request"}]}
)

print(result)
