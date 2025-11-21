import pandas as pd
import numpy as np

def calculate_skill_scores(events_df, players_df, match_df):
    """
    Calculates a skill score for each player based on their position, event data,
    and whether their team won or lost the match. The function selects the position
    with the highest skill score per player per season.

    Args:
        events_df (pd.DataFrame): DataFrame containing event data.
        players_df (pd.DataFrame): DataFrame containing player statistics and positions.
        match_df (pd.DataFrame): DataFrame containing match results.

    Returns:
        pd.DataFrame: A new DataFrame with player skill scores and their best position for each season.
    """
    print("Starting skill score calculation, including match results...")

    # Define the scoring system for each position
    scoring_rules = {
        'Raider': {
            'Super Raid': 5,
            'Raid Successful': 3,
            'Bonus Point': 1,
            'Raid Unsuccessful': -2,
            'Tackle Successful': 2,
            'Super Tackle': 3,
            'Tackle Unsuccessful': -1
        },
        'Defender': {
            'Super Tackle': 5,
            'Tackle Successful': 3,
            'Assist': 1,
            'Tackle Unsuccessful': -2,
            'Raid Successful': 2,
            'Super Raid': 3,
            'Raid Unsuccessful': -1
        },
        'All-Rounder': {
            'Super Raid': 4,
            'Raid Successful': 2,
            'Bonus Point': 1,
            'Raid Unsuccessful': -1,
            'Super Tackle': 4,
            'Tackle Successful': 2,
            'Assist': 1,
            'Tackle Unsuccessful': -1
        }
    }

    # Standardize column names for easier merging
    events_df.columns = events_df.columns.str.strip().str.lower().str.replace(' ', '_')
    players_df.columns = players_df.columns.str.strip().str.lower().str.replace(' ', '_')
    match_df.columns = match_df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    # --- IMPORTANT FIX: Standardize player and team names to fix merging issues ---
    events_df['player_name'] = events_df['player_name'].str.strip().str.lower()
    players_df['player_name'] = players_df['player_name'].str.strip().str.lower()
    
    players_df['team_name'] = players_df['team_name'].str.strip().str.lower()
    match_df['result'] = match_df['result'].str.strip().str.lower()
    # -----------------------------------------------------------------------------

    try:
        # Step 1: Merge events with match data on match_id first
        merged_df = pd.merge(events_df, match_df[['match_id', 'result']], on='match_id', how='left')
        
        # Step 2: Create a unique list of player, their team, and position for each season
        player_teams_positions = players_df[['player_name', 'season', 'position_name', 'team_name']].drop_duplicates()
        
        # Step 3: Merge the combined events/match data with player team and position data
        merged_df = pd.merge(merged_df, player_teams_positions, on=['player_name', 'season'], how='left')

        # Handle cases where a player's position or team is not in the stats file.
        merged_df['position_name'] = merged_df['position_name'].fillna('Unknown')
        merged_df['team_name'] = merged_df['team_name'].fillna('Unknown')
        merged_df['result'] = merged_df['result'].fillna('no result')

        print(f"Successfully merged data. Total events after merge: {len(merged_df)}")
        # Diagnostic check to see how many rows have an 'Unknown' position
        unknown_positions = merged_df[merged_df['position_name'] == 'Unknown']
        print(f"Number of events with 'Unknown' position after merge: {len(unknown_positions)}")

        def get_winning_team(result_string):
            """Parses the match result string to find the winning team name."""
            if pd.isna(result_string) or 'no result' in result_string:
                return None
            parts = result_string.split(' beat ')
            if len(parts) > 1:
                return parts[0].strip()
            return None

        # Apply the get_winning_team function to the result column
        merged_df['winning_team'] = merged_df['result'].apply(get_winning_team)

        # Create a new column to store the skill score for each event
        merged_df['skill_score'] = 0

        # Apply the scoring rules to each row, now with match results considered
        def assign_score(row):
            event_type = row['event_type']
            position = row['position_name']
            team_name = row['team_name']
            winning_team = row['winning_team']
            
            main_position = position.split(',')[0].strip()
            
            base_score = scoring_rules.get(main_position, {}).get(event_type, 0)
            
            if team_name == winning_team:
                bonus_multiplier = 1.25  # 25% bonus for a winning match
                return base_score * bonus_multiplier
            else:
                return base_score

        merged_df['skill_score'] = merged_df.apply(assign_score, axis=1)

        # Aggregate the scores for each player, season, and position
        player_scores = merged_df.groupby(['player_name', 'season', 'position_name'])['skill_score'].sum().reset_index()
        player_scores = player_scores.rename(columns={'skill_score': 'total_skill_score'})

        print("Initial skill scores calculated for all positions.")

        # Find the best position for each player in each season based on the highest score
        max_scores = player_scores.groupby(['player_name', 'season'])['total_skill_score'].max().reset_index()
        final_scores_df = pd.merge(max_scores, player_scores, on=['player_name', 'season', 'total_skill_score'], how='left')
        final_scores_df.drop_duplicates(subset=['player_name', 'season'], keep='first', inplace=True)

        # --- NEW LOGIC: Remove rows with a skill score of 0 and an 'Unknown' position ---
        initial_rows = len(final_scores_df)
        final_scores_df = final_scores_df[~((final_scores_df['total_skill_score'] == 0) & (final_scores_df['position_name'] == 'Unknown'))]
        rows_removed = initial_rows - len(final_scores_df)
        print(f"Removed {rows_removed} rows where skill score was 0 and position was 'Unknown'.")
        # -----------------------------------------------------------------------------

        print("Skill scores calculated successfully, with best position selected per season.")
        return final_scores_df

    except KeyError as e:
        print(f"Error: A required column was not found. Please ensure your CSV files have the columns: 'event_type', 'player_name', 'season', 'position_name', 'team_name', 'match_id', and 'result'. Missing key: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}")
        return None

if __name__ == "__main__":
    try:
        events_df = pd.read_csv('DS_event_with_timestamps_clean2.csv')
        players_df = pd.read_csv('processed_kabaddi_stats.csv')
        match_df = pd.read_csv('DS_match_modified.csv')

        print("Events, Player Stats, and Match data loaded successfully.")
        
        skill_scores_df = calculate_skill_scores(events_df, players_df, match_df)

        if skill_scores_df is not None:
            output_filename = 'mod0output/player_skill_scores.csv'
            skill_scores_df.to_csv(output_filename, index=False)
            print(f"\nPlayer skill scores have been successfully saved to '{output_filename}'.")
            
            print("\nHead of the new DataFrame:")
            print(skill_scores_df.head())
            
    except FileNotFoundError as e:
        print(f"Error: A required file was not found. Please ensure that 'DS_event_with_timestamps_clean2.csv', 'processed_kabaddi_stats.csv', and 'DS_match_modified.csv' are uploaded. Missing file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
