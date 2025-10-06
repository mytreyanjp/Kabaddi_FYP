import pandas as pd
import pulp

# Load player effectiveness data (already has "tag" column from your earlier step)
df = pd.read_csv("player_effectiveness.csv")

# Ensure tagging (reuse your logic if needed)
def tag_player(row, offense_thresh, defense_thresh):
    if row["offense_points"] >= offense_thresh and row["defense_points"] >= defense_thresh:
        return "allrounder"
    elif row["offense_points"] >= 1.2 * row["defense_points"]:
        return "raider"
    elif row["defense_points"] >= 1.2 * row["offense_points"]:
        return "defender"
    else:
        return "other"

offense_thresh = df["offense_points"].quantile(0.7)
defense_thresh = df["defense_points"].quantile(0.7)
df["tag"] = df.apply(lambda r: tag_player(r, offense_thresh, defense_thresh), axis=1)

# If no allrounder, fallback
if (df["tag"] == "allrounder").sum() == 0:
    df["allrounder_score"] = df["offense_points"] * df["defense_points"]
    fallback_idx = df["allrounder_score"].idxmax()
    df.loc[fallback_idx, "tag"] = "allrounder"

# Create ILP problem
prob = pulp.LpProblem("Optimal_Kabaddi_Team", pulp.LpMaximize)

# Decision variables: x[i] = 1 if player i is chosen
x = {i: pulp.LpVariable(f"x_{i}", cat="Binary") for i in df.index}

# Objective: maximize overall_points
prob += pulp.lpSum(df.loc[i, "overall_points"] * x[i] for i in df.index)

# Constraint: exactly 7 players
prob += pulp.lpSum(x[i] for i in df.index) == 7

# Constraint: raiders between 3 and 4
raiders = [i for i in df.index if df.loc[i, "tag"] == "raider"]
prob += pulp.lpSum(x[i] for i in raiders) >= 3
prob += pulp.lpSum(x[i] for i in raiders) <= 4

# Constraint: defenders between 3 and 4
defenders = [i for i in df.index if df.loc[i, "tag"] == "defender"]
prob += pulp.lpSum(x[i] for i in defenders) >= 3
prob += pulp.lpSum(x[i] for i in defenders) <= 4

# Constraint: at least 1 allrounder
allrounders = [i for i in df.index if df.loc[i, "tag"] == "allrounder"]
prob += pulp.lpSum(x[i] for i in allrounders) >= 1

# Solve
prob.solve(pulp.PULP_CBC_CMD(msg=False))

# Extract final team
selected_idx = [i for i in df.index if pulp.value(x[i]) == 1]
final_team = df.loc[selected_idx].reset_index(drop=True)

# Save result
final_team.to_csv("optimal_kabaddi_team_ILP.csv", index=False)

print("ILP optimal team saved to: optimal_kabaddi_team_ILP.csv")
print(final_team)
