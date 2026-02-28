from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

# temperature=0 for code generation — determinism is critical for reproducible results
code_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

# temperature=0.5 for creative/summarization tasks
creative_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.5,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

# backwards-compat alias (graphAgent, etc. still import `model`)
model = creative_llm