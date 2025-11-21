import pandas as pd
import ast

# === File paths ===
dataset_path = "MDL_pattern_dataset_v3_grok.csv"
lineup_path = "Player_Team_Lineup_merged.csv"
output_path = "MDL_pattern_dataset_v4_with_defender_ids.csv"

# === Load files ===
df = pd.read_csv(dataset_path, dtype=str)
lineup = pd.read_csv(lineup_path, dtype=str)

# Normalize names for matching
lineup["player_name_norm"] = lineup["Player Name"].str.lower().str.strip()
lineup["team_name_norm"] = lineup["Team Name"].str.lower().str.strip()

def get_defender_ids(defender_names, team_name):
    if not defender_names or defender_names == "[]" or pd.isna(defender_names):
        print("HI")
        return None
    try:
        defenders = ast.literal_eval(defender_names)
    except Exception:
        defenders = [defender_names]
    team_norm = str(team_name).lower().strip()
    ids = []
    for d in defenders:
        if not d:
            print("This happened")
            continue
        d_norm = str(d).lower().strip()
        print("#",end=" ")
        match = lineup[
            (lineup["player_name_norm"] == d_norm)
            & (lineup["team_name_norm"] == team_norm)
        ]
        if not match.empty:
            ids.append(match.iloc[0]["player_id_clean"])
        else:
            ids.append(None)
    return str(ids)

# Fill missing defender IDs
def is_empty_defender_list(val):
    """Returns True if the defender list is empty or only contains None/blank values."""
    if pd.isna(val):
        return True
    try:
        parsed = ast.literal_eval(str(val))
        if isinstance(parsed, list):
            # empty or all None/empty strings
            return all(x in [None, "None", "", "null"] for x in parsed)
    except Exception:
        pass
    return False

df["Player_Defenders_IDs"] = df.apply(
    lambda row: row["Player_Defenders_IDs"]
    if not is_empty_defender_list(row["Player_Defenders_IDs"])
    else get_defender_ids(row["Player_Defenders_Names"], row["Opponent_Team_Name"]),
    axis=1
)
# Save output
df.to_csv(output_path, index=False)
print(f"✅ Defender IDs filled and file saved as: {output_path}")
