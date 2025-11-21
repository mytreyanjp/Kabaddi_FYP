import os
import json
import pandas as pd
from collections import defaultdict

# Team name mapping
TEAM_NAME_MAP = {
    'Ben': 'Bengaluru Bulls',
    'Kol': 'Bengal Warriors',
    'Dab': 'Dabang Delhi K.C.',
    'GFG': 'Gujarat Fortunegiants',
    'Hyd': 'Telugu Titans',
    'Del': 'Dabang Delhi K.C.',
    'HS': 'Haryana Steelers',
    'Jai': 'Jaipur Pink Panthers',
    'Jaipur': 'Jaipur Pink Panthers',
    'Pat': 'Patna Pirates',
    'Pun': 'Puneri Paltan',
    'TT': 'Tamil Thalaivas',
    'Mum': 'U Mumba',
    'UPY': 'U.P. Yoddha',
    'Ben, Mum': 'Bengaluru Bulls',
}

def process_single_folder(base_dir, stat_name, data_type):
    """
    Processes all JSON files in a given folder for a specific statistic and data type.

    Args:
        base_dir (str): The base directory containing season-specific JSON files.
        stat_name (str): The name of the statistic to extract.
        data_type (str): The type of data ('player' or 'team').

    Returns:
        pd.DataFrame: A DataFrame containing the extracted data from all seasons.
    """
    data_list = []
    for season_num in range(1, 8):
        season_file = os.path.join(base_dir, f'Season_{season_num}.json')
        if not os.path.exists(season_file):
            print(f"Warning: JSON file not found for {season_file}. Skipping.")
            continue
        try:
            with open(season_file, 'r', encoding='utf-8') as f:
                season_data = json.load(f)
            if "data" in season_data and isinstance(season_data["data"], list):
                for item in season_data["data"]:
                    if isinstance(item, dict):
                        stats = defaultdict(lambda: None)
                        stats['season'] = season_num
                        stats[stat_name] = item.get('value')
                        
                        if data_type == 'player':
                            stats['player_name'] = item.get('player_name') or item.get('player')
                            stats['team_name'] = item.get('team_name') or item.get('team')
                            stats['player_id'] = item.get('player_id')
                            stats['match_played'] = item.get('match_played')
                            stats['position_id'] = item.get('position_id')
                            stats['position_name'] = item.get('position_name')
                        elif data_type == 'team':
                            stats['team_name'] = item.get('team_name') or item.get('team')
                            stats['team_id'] = item.get('team_id')
                            stats['match_played'] = item.get('match_played')

                        data_list.append(dict(stats))
                    else:
                        print(f"Warning: Found non-dictionary item in JSON list for {season_file}. Skipping item: {item}")
            else:
                print(f"Error: JSON file for {season_file} does not contain a 'data' key with a list. Skipping.")
        except json.JSONDecodeError:
            print(f"Error decoding JSON from file: {season_file}. Skipping.")
        except KeyError as e:
            print(f"Missing key in JSON file: {season_file}. Error: {e}. Skipping.")
    
    if not data_list:
        print(f"No {data_type} data was found for statistic {stat_name}. Please check your folder structure and JSON file contents.")
        return pd.DataFrame() # Return an empty DataFrame
        
    return pd.DataFrame(data_list)

def process_and_standardize(base_dirs_map, output_filename, data_type):
    """
    Processes, merges, and standardizes data from multiple folders.

    Args:
        base_dirs_map (dict): A mapping of folder names to statistic names.
        output_filename (str): The name of the output CSV file.
        data_type (str): The type of data ('player' or 'team').

    Returns:
        pd.DataFrame: The final processed DataFrame.
    """
    print(f"\nStarting data processing for {data_type} data...")
    all_data_frames = []

    for folder, stat_name in base_dirs_map.items():
        base_dir = f'./{folder}'
        print(f"Processing {data_type} folder: {base_dir} for statistic: {stat_name}")
        df_stat = process_single_folder(base_dir, stat_name, data_type)
        if not df_stat.empty:
            all_data_frames.append(df_stat)

    if not all_data_frames:
        print(f"No {data_type} data was found. Please check your folder structure and JSON file contents.")
        return None

    # Merge all dataframes on common keys (player/team name and season)
    # The first DataFrame is used as the base
    merged_df = all_data_frames[0]
    for i in range(1, len(all_data_frames)):
        # Define merge keys
        merge_keys = ['season', 'team_name']
        if data_type == 'player':
            merge_keys.append('player_name')
        
        # Merge on the keys and keep all available columns, handling suffixes for duplicates
        merged_df = pd.merge(merged_df, all_data_frames[i], on=merge_keys, how='outer', suffixes=(f'_{i-1}', f'_{i}'))

    df = merged_df
    
    # Strip whitespace from columns and convert to lowercase
    df.columns = df.columns.str.strip().str.lower()
    df.columns = df.columns.str.replace(' ', '_')

    # Standardize team names
    df['team_name'] = df['team_name'].str.strip().replace(TEAM_NAME_MAP)
    
    # Fill NaN values with a sensible default, like 0
    numeric_cols = list(base_dirs_map.values())
    df[numeric_cols] = df[numeric_cols].fillna(0)

    print("Data cleaning completed.")

    print("Starting normalization and standardization...")
    standardization_cols = list(base_dirs_map.values())
    for col in standardization_cols:
        if df[col].std() > 0:
            mean_val = df[col].mean()
            std_val = df[col].std()
            df[f'z_score_{col}'] = (df[col] - mean_val) / std_val
        else:
            df[f'z_score_{col}'] = 0
    print("Normalization and standardization completed.")

    df.to_csv(output_filename, index=False)
    print(f"\nSuccessfully processed {data_type} data and saved to '{output_filename}'.")
    return df

def calculate_player_contribution(player_df, team_df):
    """
    Merges player and team data and calculates a player's contribution to team stats.

    Args:
        player_df (pd.DataFrame): The processed player data.
        team_df (pd.DataFrame): The processed team data.

    Returns:
        pd.DataFrame: A new DataFrame with player contribution metrics.
    """
    if player_df is None or team_df is None:
        print("Error: Input DataFrames are not valid.")
        return None

    print("\nCalculating player contribution to team stats...")

    # Define a small epsilon to avoid division by zero
    epsilon = 1e-6

    # Standardize team names in both DataFrames to ensure a successful merge.
    TEAM_NAME_MAP = {
        'Ben': 'Bengaluru Bulls',
        'Beng': 'Bengal Warriors',
        'Dab': 'Dabang Delhi K.C.',
        'Guj': 'Gujarat Fortunegiants',
        'Hyd': 'Telugu Titans',
        'Jai': 'Jaipur Pink Panthers',
        'Jaipur': 'Jaipur Pink Panthers',
        'Pat': 'Patna Pirates',
        'Pun': 'Puneri Paltan',
        'Tamil': 'Tamil Thalaivas',
        'U Mumba': 'U Mumba',
        'UP Yoddha': 'U.P. Yoddha',
        'Ben, Mum': 'Bengaluru Bulls',
    }

    try:
        # Check for and rename the 'Team' column to 'team_name' if it exists.
        if 'Team' in team_df.columns:
            team_df.rename(columns={'Team': 'team_name'}, inplace=True)
            print("Renamed 'Team' column to 'team_name' in team data.")

        # Strip whitespace and check for the presence of 'team_name' column
        if 'team_name' in player_df.columns:
            player_df['team_name'] = player_df['team_name'].str.strip().replace(TEAM_NAME_MAP)
        else:
            print("Error: 'team_name' column not found in player data. Please check the spelling.")
            return None

        if 'team_name' in team_df.columns:
            team_df['team_name'] = team_df['team_name'].str.strip().replace(TEAM_NAME_MAP)
        else:
            print("Error: 'team_name' column not found in team data. Please check the spelling.")
            return None

        # Standardize other column names
        player_df.columns = player_df.columns.str.strip().str.replace(' ', '_').str.lower()
        team_df.columns = team_df.columns.str.strip().str.replace(' ', '_').str.lower()
    
    except KeyError as e:
        print(f"A KeyError occurred during data preparation: {e}. Please ensure the columns 'team_name' and other required columns exist in the input CSV files.")
        return None

    # Check if essential columns exist before attempting the merge
    required_player_cols = ['team_name', 'season', 'total_points', 'raid_points', 'tackle_points', 'do_or_die_points', 'successful_raids', 'successful_tackles', 'super_raids', 'super_tackles']
    required_team_cols = ['team_name', 'season', 'points_scored', 'raid_points', 'tackle_points', 'do_or_die_points', 'successful_raids', 'successful_tackles', 'super_raids', 'super_tackles']
    
    if not all(col in player_df.columns for col in required_player_cols):
        print("Error: Missing required columns in player data. Please check 'processed_kabaddi_stats.csv'.")
        return None
    
    if not all(col in team_df.columns for col in required_team_cols):
        print("Error: Missing required columns in team data. Please check 'processed_kabaddi_teams_stats.csv'.")
        return None
        
    # Merge the two dataframes on team_name and season, which are the correct keys
    merged_df = pd.merge(player_df, team_df, on=['team_name', 'season'], suffixes=('_player', '_team'), how='inner')

    # Check if the merged DataFrame is empty
    if merged_df.empty:
        print("Warning: The merged DataFrame is empty. This means no matching player and team data was found after cleaning. Please check team names and seasons in your CSV files.")
        return None
    
    # Calculate contribution for key metrics.
    # Note: 'total_points' is from player data, 'points_scored' from team data.
    # They are unique columns, so no suffix is added by the merge operation.
    merged_df['raid_points_contribution'] = merged_df['raid_points_player'] / (merged_df['raid_points_team'] + epsilon)
    merged_df['tackle_points_contribution'] = merged_df['tackle_points_player'] / (merged_df['tackle_points_team'] + epsilon)
    merged_df['total_points_contribution'] = merged_df['total_points'] / (merged_df['points_scored'] + epsilon)

    # Add new contribution calculations based on the provided column names
    merged_df['do_or_die_points_contribution'] = merged_df['do_or_die_points_player'] / (merged_df['do_or_die_points_team'] + epsilon)
    merged_df['successful_raids_contribution'] = merged_df['successful_raids_player'] / (merged_df['successful_raids_team'] + epsilon)
    merged_df['successful_tackles_contribution'] = merged_df['successful_tackles_player'] / (merged_df['successful_tackles_team'] + epsilon)
    merged_df['super_raids_contribution'] = merged_df['super_raids_player'] / (merged_df['super_raids_team'] + epsilon)
    merged_df['super_tackles_contribution'] = merged_df['super_tackles_player'] / (merged_df['super_tackles_team'] + epsilon)

    # Filter for the relevant columns to create the final output DataFrame
    contribution_df = merged_df[[
        'player_name', 'team_name', 'season', 'position_name',
        'raid_points_player', 'tackle_points_player', 'total_points',
        'raid_points_contribution', 'tackle_points_contribution', 'total_points_contribution',
        'do_or_die_points_contribution', 'successful_raids_contribution',
        'successful_tackles_contribution', 'super_raids_contribution',
        'super_tackles_contribution'
    ]]

    # Save the new DataFrame to a CSV file
    contribution_df.to_csv('player_contribution_stats.csv', index=False)
    print("Successfully calculated and saved player contribution stats to 'player_contribution_stats.csv'.")
    return contribution_df

if __name__ == "__main__":

    player_dirs_map = {
        'Player_do_or_die': 'do_or_die_points',
        'Player_high_5s': 'high_5s',
        'Player_avg_raid_points': 'avg_raid_points',
        'Player_raidpoints': 'raid_points',
        'Player_successful_raids' : 'successful_raids',
        'Player_successful_tackles':'successful_tackles',
        'Player_super_10s':'super_10s',
        'Player_super_raids':'super_raids',
        'Player_super_takels':'super_tackles',
        'Player_tackle_points':'tackle_points',
        'Player_Total_points':'total_points'
    }
    
    team_dirs_map = {
        'Team_Allouts_conceded': 'allouts_conceded',
        'Team_Allouts_inflicted': 'allouts_inflicted',
        'Team_avg_points_scored': 'avg_points_scored',
        'Team_avg_raid_points': 'avg_raid_points',
        'Team_avg_tackle_points': 'avg_tackle_points',
        'Team_conceded_points': 'conceded_points',
        'Team_do_die_points': 'do_or_die_points',
        'Team_points_scored': 'points_scored',
        'Team_raid_points': 'raid_points',
        'Team_successful_raids': 'successful_raids',
        'Team_successful_tackles': 'successful_tackles',
        'Team_super_raids': 'super_raids',
        'Team_super_tackles': 'super_tackles',
        'Team_tackle_points': 'tackle_points'
    }

    processed_player_df = process_and_standardize(player_dirs_map, 'processed_kabaddi_stats.csv', 'player')
    if processed_player_df is not None:
        print("\nFinal Processed Player DataFrame:")
        print(processed_player_df)

    processed_team_df = process_and_standardize(team_dirs_map, 'processed_kabaddi_teams_stats.csv', 'team')
    if processed_team_df is not None:
        print("\nFinal Processed Team DataFrame:")
        print(processed_team_df)
    
    if processed_player_df is not None and processed_team_df is not None:
        player_contribution_df = calculate_player_contribution(processed_player_df, processed_team_df)
        if player_contribution_df is not None:
            print("\nFinal Player Contribution DataFrame:")
            print(player_contribution_df.head())
