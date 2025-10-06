import pandas as pd
import numpy as np

#print("\n\n----------------------------------------------------------------------------\n\n")


# Load data
df = pd.read_csv("player_effectiveness.csv")

# Step 1: Compute 70th percentile thresholds
offense_thresh = df["offense_points"].quantile(0.7)
defense_thresh = df["defense_points"].quantile(0.7)

# Step 2: Tagging players
def tag_player(row):
    if row["offense_points"] >= offense_thresh and row["defense_points"] >= defense_thresh:
        return "allrounder"
    elif row["offense_points"] >= 1.2 * row["defense_points"]:
        return "raider"
    elif row["defense_points"] >= 1.2 * row["offense_points"]:
        return "defender"
    else:
        return "other"

df["tag"] = df.apply(tag_player, axis=1)

# Step 3: Ensure at least 1 allrounder (fallback if none qualify)
if (df["tag"] == "allrounder").sum() == 0:
    df["allrounder_score"] = df["offense_points"] * df["defense_points"]
    fallback_idx = df["allrounder_score"].idxmax()
    df.loc[fallback_idx, "tag"] = "allrounder"

# Step 4: Team selection heuristic
raiders = df[df["tag"] == "raider"].sort_values("overall_points", ascending=False)
defenders = df[df["tag"] == "defender"].sort_values("overall_points", ascending=False)
allrounders = df[df["tag"] == "allrounder"].sort_values("overall_points", ascending=False)

# Always pick 1 best allrounder (DataFrame, not list)
allrounder_pick = allrounders.iloc[[0]]

best_team = None
best_score = -1

# Try all possible splits of raiders + defenders = 6 (since 1 allrounder fixed)
for r_needed in range(2, 5):  # allow 2–4 raiders
    for d_needed in range(2, 5):  # allow 2–4 defenders
        if r_needed + d_needed != 6:
            continue

        if len(raiders) >= r_needed and len(defenders) >= d_needed and len(allrounders) >= 1:
            selected = pd.concat([
                allrounders.iloc[[0]],  # ensure at least 1 allrounder
                raiders.iloc[:r_needed],
                defenders.iloc[:d_needed]
            ])

            # ✅ extra check: must contain all 3 roles
            tags_in_team = set(selected["tag"])
            if {"raider", "defender", "allrounder"}.issubset(tags_in_team):
                score = selected["overall_points"].sum()

                if score > best_score:
                    best_score = score
                    best_team = selected


# Final team
final_team = best_team.reset_index(drop=True)

# Save
out_path = "optimal_kabaddi_with_allrounder.csv"
final_team.to_csv(out_path, index=False)

print("7-member team saved to:", out_path)
print(final_team)