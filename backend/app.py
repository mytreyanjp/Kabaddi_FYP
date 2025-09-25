'''
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

@app.route("/")
def hello_world():  
    return "<p>Hello, World!</p>"

if __name__ == '__main__':
    app.run(debug=True)

'''

'''
from flask import Flask, jsonify
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes to allow the React frontend to access the API


# A simple mock dataset for Kabaddi player data
# In a real application, this would come from a database or a complex model calculation.
mock_player_data = [
    {
        "id": 1,
        "name": "Pawan Sehrawat",
        "role": "Raider",
        "raid_points": 20,
        "tackle_points": 2,
        "offensive_value": 0.8,
        "defensive_value": 0.1
    },
    {
        "id": 2,
        "name": "Surender Nada",
        "role": "Defender",
        "raid_points": 0,
        "tackle_points": 15,
        "offensive_value": 0.05,
        "defensive_value": 0.9
    },
    {
        "id": 3,
        "name": "Sandeep Narwal",
        "role": "All-Rounder",
        "raid_points": 8,
        "tackle_points": 10,
        "offensive_value": 0.5,
        "defensive_value": 0.6
    },
    {
        "id": 4,
        "name": "Nitin Tomar",
        "role": "Raider",
        "raid_points": 18,
        "tackle_points": 1,
        "offensive_value": 0.7,
        "defensive_value": 0.15
    },
    {
        "id": 5,
        "name": "Fazel Atrachali",
        "role": "Defender",
        "raid_points": 1,
        "tackle_points": 18,
        "offensive_value": 0.02,
        "defensive_value": 0.95
    },
]


# API endpoint for player stats
@app.route("/api/player_stats", methods=["GET"])
def get_player_stats():
    """
    Returns a list of all players and their stats.
    This will be used for the Candidate Player List in the frontend.
    """
    return jsonify(mock_player_data)

# API endpoint for a specific lineup
@app.route("/api/lineup", methods=["GET"])
def get_lineup():
    """
    Runs the key points extraction, heuristics, and ILP scripts,
    then returns the optimal team as JSON.
    """
    # Step 1: Run extract_key_points, heuristics, and ilp scripts
    subprocess.run(["python", "extract_key_points.py"], check=True)
    subprocess.run(["python", "heuristics.py"], check=True)
    subprocess.run(["python", "ilp.py"], check=True)

    # Step 2: Read the generated CSV
    team_df = pd.read_csv("optimal_tamil_thalaivas_team_ILP.csv")

    # Step 3: Convert to JSON and send to frontend
    lineup = {
        "players": team_df.to_dict(orient="records"),
        # Optionally add predicted stats if available
    }
    return jsonify(lineup)

if __name__ == '__main__':
    # Run the Flask app on a specific host and port
    # host='0.0.0.0' makes the server externally visible
    app.run(debug=True, port=5000)
'''

# app.py
from flask import Flask, jsonify
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)

# Mock tactical data for a raider's path on the court.
# Coordinates are in a simplified format (x, y).
# The frontend will map these to pixels on the SVG.
mock_tactical_data = {
    "raiderPath": [
        {"x": 100, "y": 200},
        {"x": 150, "y": 180},
        {"x": 200, "y": 250},
        {"x": 300, "y": 230},
        {"x": 400, "y": 200},
        {"x": 450, "y": 210},
        {"x": 500, "y": 200}
    ]
}

# New API endpoint for tactics
@app.route("/api/tactics", methods=["GET"])
def get_tactics():
    return jsonify(mock_tactical_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)