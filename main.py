import sys
import os
from agent import callAgent
from summarizerAgent.summarizer_agent import summarize_results
import os


def main():
    """
    Main function to run the data analysis agent.
    """
    # Get user input
    user_question = input("What question do you have about the data? ")
    user_question = "Where is the top 10 places the us is spending money?"
    data_path = './data/US Spending Data/spending_data.json'
    metadata_path = './data/US Spending Data/metadata.txt'

    # Check if the data path is valid
    if not os.path.exists(data_path):
        print(f"Error: The file '{data_path}' was not found.")
        return


    
    analysis_output = callAgent(user_question, data_path)


    print(analysis_output)
        
    # 3. Summarize the results
    summary = summarize_results(user_question, analysis_output)
    
    # Present the final output
    print("\n--- Analysis Summary ---")
    print(summary)


if __name__ == "__main__":
    main()