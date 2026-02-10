from multi_tool_agent.agent import root_agent
from agent_tools.summarizer import summarize_results
import asyncio

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

async def main():
    """
    Main function to run the data analysis agent.
    """
    # Example usage:
    user_question = "What is the total spending in the dataset?"
    data_path = "data/US Spending Data/spending_data.json"

    runner = Runner()
    session_service = InMemorySessionService()
    
    session = await session_service.create_session(agent=root_agent)


    # Use the imported agent to chat
    prompt = f"""
        Use your tools to perform data analysis and answer this question:
        {user_question}
        The data is located at:
        {data_path}
        Include all python outputs and context.
        """
    

    response = await runner.run(session_id=session.id, prompt=prompt, session_service=session_service)

    
    print("RAW from agent:")
    print(f"[my_first_agent]: {response.output.text}")


    response =  summarize_results(user_question, response) 

if __name__ == "__main__":
    asyncio.run(main())