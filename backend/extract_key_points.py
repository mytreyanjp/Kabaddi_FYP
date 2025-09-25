import pandas as pd

# Load the CSV
df = pd.read_csv("player_contribution_stats.csv")

# Step 1: Identify Tamil Thalaivas players
tamil_players = df.loc[df['team_name'] == "Tamil Thalaivas", 'player_name'].unique()

# Step 2: Filter dataset to only those players
filtered = df[df['player_name'].isin(tamil_players)]

# Step 3: Define defense and offense as new columns
filtered.loc[:, "defense_points"] = (
    filtered["tackle_points_contribution"] 
    + filtered["successful_tackles_contribution"] 
    + filtered["super_tackles_contribution"]
)

filtered.loc[:, "offense_points"] = (
    filtered["raid_points_contribution"] 
    + filtered["successful_raids_contribution"] 
    + filtered["do_or_die_points_contribution"] 
    + filtered["super_raids_contribution"]
)


# Step 4: Group and average across all seasons/teams
result = filtered.groupby("player_name").agg(
    defense_points=("defense_points", "mean"),
    offense_points=("offense_points", "mean"),
    overall_points=("total_points_contribution", "mean")
).reset_index()

# Save to CSV
result.to_csv("tamil_thalaivas_player_effectiveness.csv", index=False)

print("CSV saved: tamil_thalaivas_player_effectiveness.csv")