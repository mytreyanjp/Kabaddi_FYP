# app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import subprocess
import pandas as pd
import numpy as np
import random

app = Flask(__name__)
CORS(app)

# Global flag to prevent multiple executions of the lineup optimization process
lineup_processed = False

# Cache for algorithm teams to avoid re-running
cached_ga_team = None
cached_sa_team = None
cached_tabu_team = None

# A simple mock dataset for Kabaddi player data
# In a real application, this would come from a database or a complex model calculation.


# API endpoint for player stats
@app.route("/api/player_stats", methods=["GET"])
def get_player_stats():
    """
    Returns the players from the optimal ILP team.
    This will be used for the Candidate Player List in the frontend.
    """
    try:
        ilp_df = pd.read_csv("optimal_kabaddi_team_ILP.csv")
        players = ilp_df.to_dict(orient="records")
        return jsonify(players)
    except FileNotFoundError:
        return jsonify({"error": "ILP team CSV not found. Please run the lineup optimization first."}), 404

def genetic_algorithm(players, team_size=7):
    # Simple GA to select team maximizing overall_points with role constraints
    population_size = 50
    generations = 100
    mutation_rate = 0.1

    def fitness(team):
        # Penalize if role constraints not met
        roles = [p['tag'] for p in team]
        # Enforce exactly 3 defenders, 3 raiders, 1 allrounder
        if roles.count('defender') != 3 or roles.count('raider') != 3 or roles.count('allrounder') != 1:
            return 0
        # Penalize duplicate players
        player_names = [p['player_name'] for p in team]
        if len(player_names) != len(set(player_names)):
            return 0
        return sum(p['overall_points'] for p in team)

    def create_individual():
        while True:
            individual = random.sample(players, team_size)
            roles = [p['tag'] for p in individual]
            player_names = [p['player_name'] for p in individual]
            if (roles.count('defender') == 3 and roles.count('raider') == 3 and roles.count('allrounder') == 1 and
                len(player_names) == len(set(player_names))):
                return individual

    def crossover(parent1, parent2):
        cut = random.randint(1, team_size - 1)
        child = parent1[:cut]
        for p in parent2:
            if p not in child and len(child) < team_size:
                child.append(p)
        # Ensure child has exactly team_size players
        if len(child) < team_size:
            available = [p for p in players if p not in child]
            random.shuffle(available)
            child.extend(available[:team_size - len(child)])
        return child

    def mutate(individual):
        if random.random() < mutation_rate:
            idx = random.randint(0, team_size - 1)
            new_player = random.choice(players)
            individual[idx] = new_player
        return individual

    population = [create_individual() for _ in range(population_size)]

    for _ in range(generations):
        population = sorted(population, key=fitness, reverse=True)
        next_gen = population[:10]  # Elitism
        while len(next_gen) < population_size:
            parents = random.sample(population[:20], 2)
            child = crossover(parents[0], parents[1])
            child = mutate(child)
            next_gen.append(child)
        population = next_gen

    best_team = max(population, key=fitness)
    return best_team

def simulated_annealing(players, team_size=7):
    # SA to select team maximizing overall_points with role constraints
    def fitness(team):
        roles = [p['tag'] for p in team]
        # Enforce exactly 3 defenders, 3 raiders, 1 allrounder
        if roles.count('defender') != 3 or roles.count('raider') != 3 or roles.count('allrounder') != 1:
            return 0
        # Penalize duplicate players
        player_names = [p['player_name'] for p in team]
        if len(player_names) != len(set(player_names)):
            return 0
        return sum(p['overall_points'] for p in team)

    def random_neighbor(team):
        new_team = team.copy()
        idx = random.randint(0, team_size - 1)
        new_player = random.choice(players)
        new_team[idx] = new_player
        return new_team

    current = random.sample(players, team_size)
    while True:
        roles = [p['tag'] for p in current]
        player_names = [p['player_name'] for p in current]
        if (roles.count('defender') == 3 and roles.count('raider') == 3 and roles.count('allrounder') == 1 and
            len(player_names) == len(set(player_names))):
            break
        current = random.sample(players, team_size)

    T = 100.0
    T_min = 1.0
    alpha = 0.9
    best = current
    best_score = fitness(best)

    while T > T_min:
        i = 0
        while i < 100:
            neighbor = random_neighbor(current)
            score_current = fitness(current)
            score_neighbor = fitness(neighbor)
            if score_neighbor > score_current:
                current = neighbor
                if score_neighbor > best_score:
                    best = neighbor
                    best_score = score_neighbor
            else:
                p = np.exp((score_neighbor - score_current) / T)
                if random.random() < p:
                    current = neighbor
            i += 1
        T *= alpha
    return best

def tabu_search(players, team_size=7):
    # Tabu search to select team maximizing overall_points with role constraints
    def fitness(team):
        roles = [p['tag'] for p in team]
        # Enforce exactly 3 defenders, 3 raiders, 1 allrounder
        if roles.count('defender') != 3 or roles.count('raider') != 3 or roles.count('allrounder') != 1:
            return 0
        # Penalize duplicate players
        player_names = [p['player_name'] for p in team]
        if len(player_names) != len(set(player_names)):
            return 0
        return sum(p['overall_points'] for p in team)

    def neighbors(team):
        neighs = []
        for i in range(team_size):
            for p in players:
                if p not in team:
                    new_team = team.copy()
                    new_team[i] = p
                    neighs.append(new_team)
        return neighs

    current = random.sample(players, team_size)
    while True:
        roles = [p['tag'] for p in current]
        player_names = [p['player_name'] for p in current]
        if (roles.count('defender') == 3 and roles.count('raider') == 3 and roles.count('allrounder') == 1 and
            len(player_names) == len(set(player_names))):
            break
        current = random.sample(players, team_size)

    best = current
    best_score = fitness(best)
    tabu_list = []
    max_tabu_size = 50
    iterations = 100

    for _ in range(iterations):
        neighs = neighbors(current)
        neighs = [n for n in neighs if n not in tabu_list]
        if not neighs:
            break
        current = max(neighs, key=fitness)
        current_score = fitness(current)
        if current_score > best_score:
            best = current
            best_score = current_score
        tabu_list.append(current)
        if len(tabu_list) > max_tabu_size:
            tabu_list.pop(0)
    return best

# API endpoint for a specific lineup
@app.route("/api/lineup", methods=["GET"])
def get_lineup():
    """
    Runs the key points extraction, heuristics, and ILP scripts,
    then returns the optimal team as JSON along with 3 new teams from GA, SA, and Tabu Search.
    """
    import os
    import sys

    global lineup_processed

    # Check if CSVs already exist to avoid re-running
    csvs_exist = (
        os.path.exists("player_effectiveness.csv") and
        os.path.exists("optimal_kabaddi_with_allrounder.csv") and
        os.path.exists("optimal_kabaddi_team_ILP.csv")
    )

    if not lineup_processed and not csvs_exist:
        print("Starting lineup optimization process...")

        # Ensure current working directory is backend for relative paths
        cwd = os.getcwd()
        if not cwd.endswith("backend"):
            os.chdir(os.path.join(cwd, "backend"))

        # Step 1: Run extract_key_points.py
        print("Step 1: Extracting key points from player stats...")
        subprocess.run([sys.executable, "extract_key_points.py"], check=True)
        print("Step 1 completed: Key points extracted and saved to player_effectiveness.csv")

        # Step 2: Run heuristics.py
        print("Step 2: Applying heuristics to tag players and select initial team...")
        subprocess.run([sys.executable, "heuristics.py"], check=True)
        print("Step 2 completed: Heuristic-based team saved to optimal_kabaddi_team_with_allrounder.csv")

        # Step 3: Run ilp.py
        print("Step 3: Solving Integer Linear Programming (ILP) for optimal team composition...")
        subprocess.run([sys.executable, "ilp.py"], check=True)
        print("Step 3 completed: ILP optimal team saved to optimal_kabaddi_team_ILP.csv")

        lineup_processed = True
    else:
        print("Lineup optimization already processed or CSVs exist. Skipping subprocess calls.")

    # Step 4: Read the generated CSVs
    print("Step 4: Reading the optimal team data from CSVs...")
    heuristic_df = pd.read_csv("optimal_kabaddi_with_allrounder.csv")
    ilp_df = pd.read_csv("optimal_kabaddi_team_ILP.csv")
    print(f"Heuristic team loaded: {len(heuristic_df)} players selected")
    print(f"ILP team loaded: {len(ilp_df)} players selected")

    # Prepare players list for new algorithms
    all_players_df = pd.read_csv("player_effectiveness.csv")

    # Tagging logic from heuristics.py
    offense_thresh = all_players_df["offense_points"].quantile(0.7)
    defense_thresh = all_players_df["defense_points"].quantile(0.7)

    def tag_player(row):
        if row["offense_points"] >= offense_thresh and row["defense_points"] >= defense_thresh:
            return "allrounder"
        elif row["offense_points"] >= 1.2 * row["defense_points"]:
            return "raider"
        elif row["defense_points"] >= 1.2 * row["offense_points"]:
            return "defender"
        else:
            return "other"

    all_players_df["tag"] = all_players_df.apply(tag_player, axis=1)

    # Ensure at least 1 allrounder
    if (all_players_df["tag"] == "allrounder").sum() == 0:
        all_players_df["allrounder_score"] = all_players_df["offense_points"] * all_players_df["defense_points"]
        fallback_idx = all_players_df["allrounder_score"].idxmax()
        all_players_df.loc[fallback_idx, "tag"] = "allrounder"

    all_players = all_players_df.to_dict(orient="records")

    # Generate new teams using GA, SA, and Tabu Search
    ga_team = genetic_algorithm(all_players)
    sa_team = simulated_annealing(all_players)
    tabu_team = tabu_search(all_players)

    # Save teams to CSVs for interaction matrix
    heuristic_df.to_csv("heuristic_team.csv", index=False)
    ilp_df.to_csv("ilp_team.csv", index=False)
    pd.DataFrame(ga_team).to_csv("genetic_algorithm_team.csv", index=False)
    pd.DataFrame(sa_team).to_csv("simulated_annealing_team.csv", index=False)
    pd.DataFrame(tabu_team).to_csv("tabu_search_team.csv", index=False)

    # Convert to JSON and send to frontend
    lineup = {
        "heuristic_team": {
            "players": heuristic_df.to_dict(orient="records")
        },
        "ilp_team": {
            "players": ilp_df.to_dict(orient="records")
        },
        "genetic_algorithm_team": {
            "players": ga_team
        },
        "simulated_annealing_team": {
            "players": sa_team
        },
        "tabu_search_team": {
            "players": tabu_team
        }
    }
    print("Lineup optimization process completed. Returning JSON response.")
    return jsonify(lineup)

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



@app.route("/api/interactions", methods=["GET"])
def get_interactions():
    """
    Returns the synergy matrix for the specified team using conmat.py output.
    """
    import os
    import sys

    team = request.args.get('team', 'ilp_team')
    csv_file = f"{team}.csv"
    output_csv = f"final_team_explanatory_synergy_matrix_{team}.csv"

    try:
        # Ensure current working directory is backend for relative paths
        cwd = os.getcwd()
        if not cwd.endswith("backend"):
            os.chdir(os.path.join(cwd, "backend"))

        # Check if synergy matrix CSV exists, if not, run conmat.py to generate it
        if not os.path.exists(output_csv):
            print(f"Generating synergy matrix for {team} using conmat.py...")
            subprocess.run([sys.executable, "conmat.py", csv_file, output_csv], check=True)
            print("Synergy matrix generated.")

        # Load the synergy matrix from the CSV
        synergy_df = pd.read_csv(output_csv, index_col=0)
        synergy_matrix = synergy_df.values.tolist()
        players = list(synergy_df.index)

        return jsonify({"matrix": synergy_matrix, "players": players})
    except FileNotFoundError as e:
        return jsonify({"error": f"Required file not found: {str(e)}. Ensure {csv_file} exists and datasets are available."}), 404
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Error running conmat.py: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error loading synergy matrix: {str(e)}"}), 500

# Health check endpoint for liveness and readiness probes
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
