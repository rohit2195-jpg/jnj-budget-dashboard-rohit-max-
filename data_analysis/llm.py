from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
    
load_dotenv()

modelId = os.getenv("MODEL_ID")

llm_model = ChatGoogleGenerativeAI(model=modelId, temperature=0.7)
