import pandas as pd
import re

# Load the datasets
player_stats_df = pd.read_csv('player_statistics_all_seasons.csv')
events_df = pd.read_csv('DS_event_with_timestamps_clean2.csv')  # Assuming you have this file
matches_df = pd.read_csv('DS_match_modified.csv')  # Assuming you have this file

# Function to extract team names from match result
def extract_teams_from_result(result):
    if pd.isna(result):
        return None, None
    
    # Pattern to extract teams from result string
    pattern = r'(.+?)\s+(?:beat|tied with|drew with)\s+(.+?)\s+\([0-9]+\s*[-–]\s*[0-9]+\)'
    match = re.search(pattern, result)
    
    if match:
        team1 = match.group(1).strip()
        team2 = match.group(2).strip()
        return team1, team2
    else:
        # Try alternative pattern if the first one doesn't match
        pattern2 = r'(.+?)\s+vs\s+(.+)'
        match2 = re.search(pattern2, result)
        if match2:
            return match2.group(1).strip(), match2.group(2).strip()
        return None, None

# Create a dictionary to map match_id to teams
match_teams = {}
for _, row in matches_df.iterrows():
    team1, team2 = extract_teams_from_result(row['result'])
    if team1 and team2:
        match_teams[row['match_id']] = (team1, team2)

# Create a dictionary for player seasons and teams
player_season_teams = {}
for _, row in player_stats_df.iterrows():
    key = (row['Player Name'], row['Season'])
    if key not in player_season_teams:
        player_season_teams[key] = set()
    player_season_teams[key].add(row['Team'])

# Check consistency in events dataset
inconsistent_records = []

for idx, event in events_df.iterrows():
    player_name = event['player_name']
    season = event['season']
    match_id = event['match_id']
    
    # Check if player played in this season
    key = (player_name, season)
    if key not in player_season_teams:
        inconsistent_records.append({
            'event_id': event['event_id'],
            'player_name': player_name,
            'season': season,
            'match_id': match_id,
            'issue': f"Player {player_name} not found in season {season}"
        })
        continue
    
    # Check if match_id exists in our matches data
    if match_id not in match_teams:
        inconsistent_records.append({
            'event_id': event['event_id'],
            'player_name': player_name,
            'season': season,
            'match_id': match_id,
            'issue': f"Match ID {match_id} not found in matches data"
        })
        continue
    
    # Check if player's team participated in this match
    team1, team2 = match_teams[match_id]
    player_teams = player_season_teams[key]
    
    if team1 not in player_teams and team2 not in player_teams:
        inconsistent_records.append({
            'event_id': event['event_id'],
            'player_name': player_name,
            'season': season,
            'match_id': match_id,
            'issue': f"Player {player_name} played for {list(player_teams)} in season {season}, but match {match_id} was between {team1} and {team2}"
        })

# Display results
if inconsistent_records:
    print(f"Found {len(inconsistent_records)} inconsistent records:")
    for record in inconsistent_records[:10]:  # Show first 10 issues
        print(record)
    
    # Create DataFrame of issues
    issues_df = pd.DataFrame(inconsistent_records)
    
    # Save to CSV for review
    issues_df.to_csv('inconsistent_records.csv', index=False)
    print("\nFull list of inconsistent records saved to 'inconsistent_records.csv'")
else:
    print("All records are consistent!")

# Function to fix inconsistent records by finding the correct season
def find_correct_season(player_name, match_id):
    if match_id not in match_teams:
        return None
    
    team1, team2 = match_teams[match_id]
    
    # Find all seasons where this player played for either team
    possible_seasons = []
    for (p_name, season), teams in player_season_teams.items():
        if p_name == player_name and (team1 in teams or team2 in teams):
            possible_seasons.append(season)
    
    return possible_seasons[0] if possible_seasons else None

# Fix the inconsistent records in a copy of the events dataframe
fixed_events_df = events_df.copy()

for idx, record in enumerate(inconsistent_records):
    event_id = record['event_id']
    player_name = record['player_name']
    match_id = record['match_id']
    
    correct_season = find_correct_season(player_name, match_id)
    if correct_season:
        # Update the season in the fixed dataframe
        fixed_events_df.loc[fixed_events_df['event_id'] == event_id, 'season'] = correct_season
        print(f"Fixed event {event_id}: {player_name} season changed to {correct_season}")

# Save the fixed events dataframe
fixed_events_df.to_csv('fixed_events_dataset.csv', index=False)
print("Fixed events dataset saved to 'fixed_events_dataset.csv'")