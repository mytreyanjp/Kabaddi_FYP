import pandas as pd
import json
import random
from ast import literal_eval

# === File paths ===
csv_path = "MDL_pattern_dataset_v2.csv"
json_path = "Season_5_matches.json"
lineup_path = "Player_Team_Lineup_merged.csv"
out_csv = "MDL_pattern_dataset_v3_grok.csv"

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

# === Robust parser for existing columns ===
def safe_parse(col):
    if not col or str(col).strip() in {"", "None", "[]", "['[]']", "[None]"}:
        return []
    try:
        val = literal_eval(col)
        if isinstance(val, list):
            return [str(x).strip() for x in val if x not in {"", None}]
    except Exception:
        pass
    # fallback comma split
    return [x.strip() for x in str(col).split(",") if x.strip()]

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

    # === Robust parsing of existing columns ===
    names_raw = row.get("Player_Defenders_Names", "")
    ids_raw   = row.get("Player_Defenders_IDs", "")
    defenders     = safe_parse(names_raw)
    defender_ids  = safe_parse(ids_raw) if ids_raw else []

    # Only fetch from JSON when truly empty — pick a random subset of available defenders
    if not defenders:
        all_defenders = get_defenders_for_team(match_id, opponent_team)
        if all_defenders:
            # choose a random number of defenders between 1 and total available
            k = random.randint(1, len(all_defenders))
            defenders = random.sample(all_defenders, k)
        else:
            defenders = []
        defender_ids = map_to_ids(opponent_team, defenders)

    # If we have names but not ids, attempt to map them
    if defenders and (not defender_ids or len(defender_ids) != len(defenders)):
        defender_ids = map_to_ids(opponent_team, defenders)

    # === Adjust defenders for Successful Raid (only when raid points > 0) ===
    outcome = str(row.get("Event_Outcome", "")).lower()
    raid_pts = None
    try:
        sb = int(float(row.get("Score_Before", 0)))
        sa = int(float(row.get("Score_After", 0)))
        raid_pts = sa - sb
    except Exception:
        raid_pts = None

    if outcome.startswith("success") and defenders and raid_pts is not None and raid_pts > 0:
        num_remove = min(raid_pts, len(defenders))
        if num_remove > 0:
            defenders = defenders[:-num_remove] if num_remove < len(defenders) else []
            if defender_ids:
                defender_ids = defender_ids[:-num_remove] if num_remove < len(defender_ids) else []

    # Final write – always store Python list strings
    df.at[i, "Player_Defenders_Names"] = str(defenders)
    df.at[i, "Player_Defenders_IDs"]   = str(defender_ids or [])

# === Save cleaned dataset ===
df.to_csv(out_csv, index=False)
print(f"✅ Cleaned dataset saved as {out_csv}")