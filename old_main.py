import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_tools.analyzer import generate_analysis_code, execute_analysis
from agent_tools.summarizer import summarize_results
import os

def main():
    """
    Main function to run the data analysis agent.
    """
    # Get user input
    user_question = input("What question do you have about the data? ")
    data_path = './data/US Spending Data/spending_data.json'
    metadata_path = './data/US Spending Data/metadata.txt'

    # Check if the data path is valid
    if not os.path.exists(data_path):
        print(f"Error: The file '{data_path}' was not found.")
        return


    analysis_code = generate_analysis_code(user_question, data_path)
    

    analysis_output = execute_analysis(analysis_code)
    print(analysis_output)
 
        
    # 3. Summarize the results
    summary = summarize_results(user_question, analysis_output)
    
    # Present the final output
    print("\n--- Analysis Summary ---")
    print(summary)


if __name__ == "__main__":
    main()