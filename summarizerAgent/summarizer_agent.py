from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
import os
from dotenv import load_dotenv
from summarizerAgent.tools import save_analysis_to_txt
from agent_tools.llm_model import model


load_dotenv()


SUMMARIZER_SYSTEM = """You are a senior data analyst who writes precise, number-anchored markdown reports.

RULES:
1. Every section must cite at least one specific number — no section may contain only qualitative prose
2. Use the exact unit label from the "unit" field when citing numbers
3. Bold the single most important number in each section using **value**
4. For rankings, cite the top 3 and the bottom 1 by name and value
5. For timeseries, identify the highest and lowest points by label and value

GOOD section example:
### Top Recipients by Award Amount
EXXON MOBIL CORPORATION received the largest award at **$724,234,597 USD**, followed by ELECTRIC BOAT CORPORATION at $609,128,749 USD. Together the top 2 recipients account for $1,333,363,346 USD — roughly 67% of total spend. At the bottom, P.M. BROGAN, INC. received only $11,537 USD.

BAD section example (never write like this):
### Top Recipients by Award Amount
The analysis identified the highest funded recipients. Major corporations dominated the top of the list, while small businesses appeared at the bottom."""


agent = create_agent(model, tools=[save_analysis_to_txt])


def summarize_results(user_question, analysis_output, outputFilePath):

    invoke_result = agent.invoke(
        {
            "messages": [
                {"role": "system", "content": SUMMARIZER_SYSTEM},
                {"role": "user", "content": f"""The user asked: "{user_question}"

Structured analysis results:
---
{analysis_output}
---

Write a markdown report with:
- ## Executive Summary at the top (3–5 sentences, cite the 2 most important numbers)
- One ### section per output_label using "title" as the heading
- Each section must cite specific values from "values" or "series" with the correct "unit"
- ## Additional Insights section at the end

Save the report using save_analysis_to_txt to: {outputFilePath}
Return the exact markdown content as your final message.
Do not describe what you are doing."""}
            ]
        }
    )

    last_message = invoke_result["messages"][-1]
    content = last_message.content
    if isinstance(content, list):
        return content[0].get("text", "")
    return content
