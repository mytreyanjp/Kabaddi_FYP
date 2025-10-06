import pandas as pd
import random
import re

def fill_home_team_name(row):
    """
    Checks if home_team_name is missing. If so, it extracts the two
    competing teams from the 'result' column and randomly chooses one
    to be the home team.
    """
    # Check if the home_team_name column is empty for the current row
    if pd.isna(row['home_team_name']):
        result_text = row['result']
        
        # Ensure the result is a string and indicates a winner
        if isinstance(result_text, str) and 'beat' in result_text:
            # Use regex to find the two team names
            # This pattern is flexible to handle different spacing
            teams = re.findall(r'(.+?)\s+beat\s+(.+?)\s*\(', result_text)
            
            if teams:
                # teams is a list of tuples, e.g., [('Team A', 'Team B')]
                all_teams = list(teams[0])
                return random.choice(all_teams)
                
    # If home_team_name is not missing or can't be filled, return the original value
    return row['home_team_name']

# --- Main script execution ---

# 1. Load the dataset from a CSV file
# IMPORTANT: Replace 'your_data.csv' with the actual name of your file.
try:
    df = pd.read_csv('DS_match_modified.csv')
    print("✅ File loaded successfully.")
except FileNotFoundError:
    print("❌ Error: Could not find the file 'your_data.csv'.")
    print("Please make sure your data file is in the same folder as this script and the filename is correct.")
    exit()

# 2. Apply the function to fill in the missing home team names
print("Processing data to fill missing home team names...")
df['home_team_name'] = df.apply(fill_home_team_name, axis=1)
print("✅ Processing complete.")

# 3. Save the modified DataFrame to a new CSV file
output_filename = 'DS_match_modified.csv'
df.to_csv(output_filename, index=False)
print(f"✅ DataFrame saved successfully to {output_filename}")