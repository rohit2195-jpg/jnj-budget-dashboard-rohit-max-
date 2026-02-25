import sys
import os
from agent_tools.agent import callAgent
from summarizerAgent.summarizer_agent import summarize_results
from pre_processing.processing_agent import callPreProcessAgent
from plannerAgent.planner_agent import create_analysis_plan
from graphAgent.graphAgent import create_graph


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
    manifest = callPreProcessAgent(data_path)
    print("Preprocessing complete. Manifest:", manifest)

    if manifest.get("status") == "error":
        print(f"Preprocessing failed: {manifest.get('error')}")
        return

    # Build analysis checklist from schema + question before running the analyst
    plan = create_analysis_plan(user_question, manifest)

    # Calling Task agent to perform analysis on the data
    analysis_output = callAgent(user_question, manifest, plan)

    print(analysis_output)
        
    # 3. Summarize the results

    graph_json = create_graph(user_question=user_question, analysis_output=analysis_output)
    print(graph_json)
    
    summary = summarize_results(user_question, analysis_output, ouptut_file_path)
    
    # Present the final output
    print("\n--- Analysis Summary ---")
    print(summary)
    
    


if __name__ == "__main__":
    main()