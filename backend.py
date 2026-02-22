import sys
import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

from agent_tools.agent import callAgent
from summarizerAgent.summarizer_agent import summarize_results
from pre_processing.processing_agent import callPreProcessAgent
from graphAgent.graphAgent import create_graph

app = Flask(__name__)
CORS(app)

@app.route('/api/analyze', methods=['POST'])
def analyze_data():
    """
    REST API endpoint that receives a user question, runs the analysis pipeline, 
    and returns the summary markdown and graph JSON to the frontend.
    """
    try:
        # 1. Extract data from the incoming request
        data = request.json
        if not data:
            return jsonify({"error": "No JSON payload provided"}), 400

        user_question = data.get('question')
        
        # You can either pass this from frontend or hardcode it if it's always the same
        data_path = data.get('filepath', 'data/f1/F1 2026 Bahrain Testing Day 3.csv')
        # metadata_path = './data/US Spending Data/metadata.txt'
        output_file_path = ''

        if not user_question:
            return jsonify({"error": "Missing 'question' in request body"}), 400
            
        if not os.path.exists(data_path):
            return jsonify({"error": f"The file '{data_path}' was not found."}), 404

        print(f"Starting analysis for question: {user_question}")

        # 2. Pre-processing
        pre_process_output = callPreProcessAgent(data_path)
        print("Pre-processing complete.", pre_process_output)
        
        # 3. Data Analysis
        analysis_output = callAgent(user_question, pre_process_output)
        print("Analysis complete.", analysis_output)
        
        # 4. Generate Graph Configurations
        graph_json_string = create_graph(user_question=user_question, analysis_output=analysis_output)
        print("Graph generation complete.")
        
        try:
            # Parse the string returned by the LLM into actual JSON
            graph_data = json.loads(graph_json_string)
            print(graph_data)
        except json.JSONDecodeError:
            print("Failed to parse AI graph output as JSON. Output was:", graph_json_string)
            # Fallback so frontend doesn't crash
            graph_data = {"charts": []}

        # 5. Summarize Results (Markdown)
        summary = summarize_results(user_question, analysis_output, output_file_path)
        print("Summary complete.", summary)
        
        # 6. Return payload
        return jsonify({
            "success": True,
            "summary": str(summary),
            "graphs": graph_data
        }), 200

    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5001)
