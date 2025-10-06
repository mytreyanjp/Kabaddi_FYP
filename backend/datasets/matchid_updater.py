import pandas as pd
import re

# Load datasets
events = pd.read_csv("DS_event_with_timestamps.csv")
matches = pd.read_csv("DS_match_modified.csv")
player_stats = pd.read_csv("player_statistics_all_seasons.csv")

# Normalize columns for consistency
player_stats.rename(columns={"Player Name": "player_name", "Season": "season"}, inplace=True)
player_stats["player_name"] = player_stats["player_name"].str.strip().str.lower()
events["player_name"] = events["player_name"].str.strip().str.lower()

# Step 1: Extract team names from match results
def extract_teams(result):
    if pd.isna(result):
        return []
    parts = re.split(r" beat |\(|\)", str(result))
    return [p.strip() for p in parts if p and not p.strip().isdigit() and "-" not in p]

matches["teams"] = matches["result"].apply(extract_teams)

# Step 2: Build player -> team mapping
player_team_map = player_stats.groupby(["player_name", "season"])["Team"].first().to_dict()

# Step 3: Correct match_id if wrong
def correct_match_id(row):
    player = row["player_name"]
    season = row["season"]
    match_id = row["match_id"]
    player_team = player_team_map.get((player, season), None)

    if player_team is None:
        return match_id
    
    # Check current match teams
    teams = matches.loc[matches["match_id"] == match_id, "teams"]
    if not teams.empty and player_team in teams.iloc[0]:
        return match_id
    
    # Find an alternative valid match in same season
    possible_matches = matches[(matches["season"] == season) & 
                               (matches["teams"].apply(lambda x: player_team in x if isinstance(x, list) else False))]
    if not possible_matches.empty:
        return possible_matches.iloc[0]["match_id"]
    
    return match_id

# Apply correction to events dataset
events["match_id"] = events.apply(correct_match_id, axis=1)

# Step 4: Save outputs as CSV (no ZIP)
events.to_csv("DS_event_with_timestamps_clean2.csv", index=False)
matches.to_csv("DS_match_modified_clean.csv", index=False)

print("✅ Cleaned CSV files created:")
print(" - DS_event_with_timestamps_clean.csv")
print(" - DS_match_modified_clean.csv")
