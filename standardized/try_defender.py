import pandas as pd
import json
import random
from ast import literal_eval

# === File paths ===
csv_path = "MDL_pattern_dataset_v2.csv"
json_path = "Season_5_matches.json"
lineup_path = "Player_Team_Lineup_merged.csv"
out_csv = "MDL_pattern_dataset_v3.csv"

# === Load data ===
df = pd.read_csv(csv_path, dtype=str)
with open(json_path, "r", encoding="utf-8") as f:
    matches = json.load(f)
lineup = pd.read_csv(lineup_path, dtype=str)

# === Normalize names for mapping ===
lineup["player_name_norm"] = lineup["Player Name"].str.lower().str.strip()
lineup["team_name_norm"] = lineup["Team Name"].str.lower().str.strip()
player_id_lookup = {
    (r["team_name_norm"], r["player_name_norm"]): r.get("player_id_clean")
    for _, r in lineup.iterrows()
}
match_map = {str(m["match_id"]): m for m in matches if isinstance(m, dict) and "match_id" in m}

# === Helper: get defenders for a team ===
def get_defenders_for_team(match_id, team_name):
    """
    Return list of defender player names for given match_id and team_name.
    """
    m = match_map.get(str(match_id))
    if not m or "teams" not in m:
        return []
    defenders = []
    for team in m.get("teams", []):
        tn = team.get("team_name") or team.get("team")
        if not tn:
            continue
        if str(tn).lower().strip() == str(team_name).lower().strip():
            for p in team.get("players", []) or []:
                cat = str(p.get("category", "")).lower()
                if "defender" in cat:
                    name = p.get("name") or p.get("player_name") or p.get("full_name")
                    if name:
                        defenders.append(str(name).strip())
            break
    return defenders

# === Helper: map names to IDs ===
def map_to_ids(team_name, player_names):
    ids = []
    for p in player_names:
        key = (str(team_name).lower().strip(), str(p).lower().strip())
        ids.append(player_id_lookup.get(key))
    return ids

# === Pre-clean: remove unwanted non-raid rows ===
drop_keywords = ["timeout", "official", "technical", "substitution", "review"]
mask = df["Raid_Type"].fillna("").str.lower().apply(
    lambda x: not any(k in x for k in drop_keywords)
)
df = df[mask].reset_index(drop=True)

# === Fill missing defenders ONLY for Season 5 and using Match_ID + Opponent_Team_Name ===
for i, row in df.iterrows():
    if str(row.get("Season_Number")).strip() != "5":
        continue

    match_id = row.get("Match_ID")
    opponent_team = row.get("Opponent_Team_Name")  # use opponent as the defending team
    if not match_id or not opponent_team:
        continue

    # Skip non-raid events again defensively
    rt = str(row.get("Raid_Type", "")).lower()
    if any(k in rt for k in drop_keywords) or rt.strip() == "":
        continue

    # Parse existing defenders names and ids (if present)
    defenders = []
    defender_ids = []
    names_raw = row.get("Player_Defenders_Names", "")
    ids_raw = row.get("Player_Defenders_IDs", "")

    # Try to parse existing names
    if names_raw and names_raw.strip() not in ["", "None", "[]"]:
        try:
            parsed = literal_eval(names_raw)
            if isinstance(parsed, list):
                defenders = [str(x).strip() for x in parsed if x not in ["", None]]
        except Exception:
            # fallback: treat as comma-separated
            defenders = [x.strip() for x in str(names_raw).split(",") if x.strip()]

    # Try to parse existing ids
    if ids_raw and ids_raw.strip() not in ["", "None", "[]"]:
        try:
            parsed_ids = literal_eval(ids_raw)
            if isinstance(parsed_ids, list):
                defender_ids = parsed_ids
        except Exception:
            defender_ids = [None] * len(defenders)

    # If defenders list is empty, fetch from JSON using Opponent_Team_Name + Match_ID
    if not defenders:
        defenders = get_defenders_for_team(match_id, opponent_team)
        defender_ids = map_to_ids(opponent_team, defenders)

    # If we have names but not ids, attempt to map them
    if defenders and (not defender_ids or len(defender_ids) != len(defenders)):
        defender_ids = map_to_ids(opponent_team, defenders)

    # === Adjust defenders if Successful Raid ===
    outcome = str(row.get("Event_Outcome", "")).lower()
    # compute raid points if possible
    raid_pts = None
    try:
        sb = int(float(row.get("Score_Before", 0)))
        sa = int(float(row.get("Score_After", 0)))
        raid_pts = sa - sb
    except Exception:
        raid_pts = None

    if outcome.startswith("success") and defenders:
        # Determine number to remove: at least 1, prefer raid_pts if available
        if raid_pts is None:
            num_remove = 1
        else:
            # remove up to raid_pts (or at least 1). Do not attempt to remove negative.
            num_remove = max(1, raid_pts)
        # cap removal to available defenders
        num_remove = min(num_remove, len(defenders))
        if num_remove > 0:
            # remove from the end (assume list order not critical). Adjust ids accordingly.
            defenders = defenders[:-num_remove] if num_remove < len(defenders) else []
            if defender_ids:
                defender_ids = defender_ids[:-num_remove] if num_remove < len(defender_ids) else []

    # Ensure both columns are updated as Python lists serialized to string
    df.at[i, "Player_Defenders_Names"] = str(defenders)
    df.at[i, "Player_Defenders_IDs"] = str(defender_ids)

# === Save cleaned dataset ===
df.to_csv(out_csv, index=False)
print(f"✅ Cleaned dataset saved as {out_csv}")
