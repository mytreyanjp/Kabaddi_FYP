import pandas as pd

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
    # This is critical to handle minor inconsistencies like 'U Mumba' vs 'U Mumba '.
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
    contribution_df.to_csv('mod0output/player_contribution_stats.csv', index=False)
    print("Successfully calculated and saved player contribution stats to 'player_contribution_stats.csv'.")
    return contribution_df

# Load the necessary files and execute the function
try:
    df_processed_stats = pd.read_csv('processed_kabaddi_stats.csv')
    df_processed_teams = pd.read_csv('processed_kabaddi_teams_stats.csv')

    player_contribution_df = calculate_player_contribution(df_processed_stats, df_processed_teams)

    if player_contribution_df is not None:
        print("\nFinal Processed Player Contribution DataFrame:")
        print(player_contribution_df.head())

except Exception as e:
    print(f"An error occurred: {e}")
