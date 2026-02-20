import sys
import os
from agent_tools.agent import callAgent
from summarizerAgent.summarizer_agent import summarize_results
from pre_processing.processing_agent import callPreProcessAgent
import os


def main():
    """
    Main function to run the data analysis agent.
    """
    # Get user input
    #user_question = input("What question do you have about the data? ")
    user_question = "What are the top 5 most and least areas where the US spends money"
    data_path = './data/US Spending Data/spending_data.json'
    metadata_path = './data/US Spending Data/metadata.txt'

    ouptut_file_path = ''

    # Check if the data path is valid
    if not os.path.exists(data_path):
        print(f"Error: The file '{data_path}' was not found.")
        return
    
    # preprocessing
    pre_process_ouptut = callPreProcessAgent(data_path)
    print("pre_process_ouptut: ", pre_process_ouptut)

    
    # Calling Task agent to perform analysis on the data
    analysis_output = callAgent(user_question, pre_process_ouptut)

    print(analysis_output)
        
    # 3. Summarize the results
    
    summary = summarize_results(user_question, analysis_output, ouptut_file_path)
    
    # Present the final output
    print("\n--- Analysis Summary ---")
    print(summary)
    
    


if __name__ == "__main__":
    main()