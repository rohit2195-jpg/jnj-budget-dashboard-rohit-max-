from langchain.agents.react.agent import create_react_agent
from langchain.agents import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool

from data_analysis.tools import generate_analysis_code_tool, execute_analysis_tool
import os
from dotenv import load_dotenv

from data_analysis.llm import llm_model


tools = [generate_analysis_code_tool, execute_analysis_tool]

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a data analysis agent. "
        "Use tools to generate and execute Python analysis code."
    ),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])


agent = create_react_agent(
    llm=llm_model,
    tools=[echo_tool],
    prompt=prompt,
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=[echo_tool],
    verbose=True,
)

