import pandas as pd

try:
    print("--- Checking column names ---")
    
    # --- Check the player statistics file ---
    player_stats_df = pd.read_csv("datasets/player_statistics_all_seasons.csv")
    print("\nColumns in 'player_statistics_all_seasons.csv':")
    print(player_stats_df.columns.tolist())
    print("-" * 50)

    # --- Check the match results file ---
    match_results_df = pd.read_csv("datasets/DS_match_modified.csv")
    print("Columns in 'DS_match_modified.csv':")
    print(match_results_df.columns.tolist())
    print("-" * 50)

except FileNotFoundError as e:
    print(f"Error: A file was not found. {e}")
except Exception as e:
    print(f"An error occurred: {e}")