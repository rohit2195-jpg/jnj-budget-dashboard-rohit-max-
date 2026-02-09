from data_analysis.llm_agent import agent
from data_analysis.summarizer import summarize_results

def main():
    """
    Main function to run the data analysis agent.
    """
    # Example usage:
    user_question = "What is the total spending in the dataset?"
    data_path = "data/US Spending Data/spending_data.json"

    # Use the imported agent to chat
    response = agent.chat(f"Use your tools to perform data analysis and answer this question: {user_question} for the data at {data_path}")
    
    print("RAW from agent:")
    print(response)

    response =  summarize_results(user_question, response) 

if __name__ == "__main__":
    main()