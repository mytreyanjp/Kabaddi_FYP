import pandas as pd

# Load the CSV
try:
    df = pd.read_csv("player_contribution_stats.csv")

    # Use .copy() to avoid potential warnings later
    filtered = df.copy()

    # Define new columns using the CORRECT column names from your CSV
    # Using 'tackle_points_player', 'raid_points_player', and 'total_points'
    filtered.loc[:, "defense_points"] = filtered["tackle_points_player"]
    filtered.loc[:, "offense_points"] = filtered["raid_points_player"]
    filtered.loc[:, "overall_points"] = filtered["total_points"]

    # Group by the correct player name column 'player_name'
    result = filtered.groupby("player_name").agg(
        defense_points=("defense_points", "mean"),
        offense_points=("offense_points", "mean"),
        overall_points=("overall_points", "mean")
    ).reset_index()

    # Save to a new CSV
    result.to_csv("player_effectiveness.csv", index=False)

    print("CSV saved successfully: player_effectiveness.csv")

except FileNotFoundError:
    print("Error: 'player_contribution_stats.csv' not found. Please ensure the file is in the correct directory.")
except KeyError as e:
    print(f"Error: A column was not found in the CSV. Please check the column names. Missing column: {e}")