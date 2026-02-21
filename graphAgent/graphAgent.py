from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
import os
from dotenv import load_dotenv
from graphAgent.tools import save_graph_to_file
from agent_tools.llm_model import model


load_dotenv()


agent = create_agent(model, tools=[])


def create_graph(user_question, analysis_output):

 
    prompt_template = f"""
     You are an expert data visualization API. Your task is to take a user's question and a data analysis output, and generate a JSON payload to render dynamic charts
      using the ApexCharts library.
    
     CRITICAL INSTRUCTIONS:
     1. Return ONLY valid JSON. Do not include markdown formatting like ```json, and do not include any conversational text, preamble, or explanations.
     2. The root of the JSON must be an object with a single key "charts" containing an array of chart objects.
    3. Select the best chart types ("line", "bar", "area", "pie", "donut") to answer the user's question based on the data.
   

  CHART OBJECT SCHEMA:
  Every chart object in the array must strictly follow this format:
   - "id": A unique string ID (e.g., "sales-trend-1").
   - "title": A descriptive string title for the chart.
   - "type": The type of chart ("line", "bar", "area", "pie", "donut").
   - "series": The data payload. MUST follow the strict type rules below.
   - "options": The ApexCharts configuration. MUST follow the strict type rules below.

  TYPE-SPECIFIC RULES (CRITICAL):


  Rule A: For "line", "bar", or "area" charts:
   - series MUST be an array of objects. Each object needs a "name" (string) and "data" (array of numbers).
    Example: "series": [{{"name": "Revenue", "data": [100, 200, 300]}}]
   - options MUST include an "xaxis" object containing a "categories" array (strings) that maps to the data points.
    Example: "options": {{ "xaxis": {{ "categories": ["Jan", "Feb", "Mar"] }} }}


  Rule B: For "pie" or "donut" charts:
   - series MUST be a flat array of numbers.
    Example: "series": [44, 55, 13]
   - options MUST include a "labels" array (strings) mapping to the series numbers.
    Example: "options": {{ "labels": ["Apples", "Oranges", "Bananas"] }}


  INPUT:
  User Question: "{user_question}"
  Data Analysis Output:
  ---
  {analysis_output}
  ---


  Generate the JSON payload now:
  """

    analysis_output = agent.invoke(
          {"messages": [{"role": "user", "content": prompt_template}]}
      )

    last_message = analysis_output["messages"][-1]
    content = last_message.content
    if isinstance(content, str):
        content = content.replace("json", "").replace("", "").strip()
    content = content.strip('```').strip('\n')
    return content

