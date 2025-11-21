import json
import pandas as pd
import numpy as np
import re
from ast import literal_eval
from collections import defaultdict

# -------- CONFIG (change if needed) --------
INPUT_CSV = "MDL_pattern_dataset_v3_no_season5.csv"
LINEUP_CSV = "Player_Team_Lineup_merged.csv"
MATCHES_JSON = "Season_5_matches.json"   # or a consolidated matches JSON (contains 'teams' with 'players')
OUTPUT_CSV = "MDL_pattern_dataset_preprocessed.csv"

# -------- Helpers --------
def norm(s):
    if pd.isna(s):
        return ""
    return str(s).strip().lower()

def parse_list_field(s):
    # robustly parse things like "[]", "[None]", "['[]']" or "['A','B']"
    if pd.isna(s): return []
    ss = str(s).strip()
    if ss in ["","[]","[None]","['[]']","None"]:
        return []
    try:
        val = literal_eval(ss)
        if isinstance(val, list):
            return [str(x).strip() for x in val if x and str(x).strip() and str(x).strip().lower() not in ['none','nan','[]']]
    except:
        # fallback split
        parts = re.split(r'[,\|;]', ss)
        return [p.strip() for p in parts if p.strip() and p.strip().lower() not in ['none','nan','[]']]
    return []

# -------- Load files --------
print("Loading CSV and lineup...")
df = pd.read_csv(INPUT_CSV, dtype=str, low_memory=False)
lineup = pd.read_csv(LINEUP_CSV, dtype=str, low_memory=False)

# Normalize lineup for lookup
lineup['player_name_norm'] = lineup['Player Name'].fillna('').str.lower().str.strip()
lineup['team_name_norm'] = lineup['Team Name'].fillna('').str.lower().str.strip()
lineup_lookup = {}
for _, r in lineup.iterrows():
    key = (str(r['team_name_norm']), str(r['player_name_norm']))
    lineup_lookup[key] = r.get('player_id_clean')

# Load matches JSON (if available)
matches_map = {}
try:
    with open(MATCHES_JSON, 'r', encoding='utf-8') as f:
        matches = json.load(f)
    # If matches is a list of dicts with 'match_id' and 'teams'
    for m in matches:
        mid = str(m.get('match_id') or m.get('id') or m.get('Match_ID') or "").strip()
        if mid:
            matches_map[mid] = m
    print("Loaded matches json entries:", len(matches_map))
except Exception as e:
    print("Could not load matches JSON:", e)
    matches_map = {}

# -------- 1) Fill defender NAMES from match JSON when missing --------
print("Filling defender names from match JSON where empty...")
def get_defenders_from_match(match_id, team_name):
    m = matches_map.get(str(match_id))
    if not m:
        return []
    team_name_norm = norm(team_name)
    defenders = []
    teams = m.get('teams') or m.get('Teams') or []
    for t in teams:
        if norm(t.get('team_name') or t.get('Team Name')) == team_name_norm:
            players = t.get('players') or t.get('Players') or []
            for p in players:
                cat = str(p.get('category','') or '').lower()
                if 'defender' in cat:  # captures "Defender, left cover" etc.
                    name = p.get('name') or p.get('player_name') or p.get('Name')
                    if name: defenders.append(str(name).strip())
            break
    return defenders

# parse existing defenders column to python lists
df['_defs_names'] = df['Player_Defenders_Names'].apply(parse_list_field)
df['_defs_ids'] = df['Player_Defenders_IDs'].apply(parse_list_field)

rows_filled = 0
for i,row in df.iterrows():
    if len(row['_defs_names'])==0:
        mid = str(row.get('Match_ID') or "").strip()
        opp = row.get('Opponent_Team_Name') or row.get('Raider_Team_Name') or ""
        # defenders are from opponent team (they defend against raider)
        defenders = get_defenders_from_match(mid, opp)
        if defenders:
            df.at[i,'_defs_names'] = defenders
            rows_filled += 1

print("Defender NAMES filled from match JSON for rows:", rows_filled)

# -------- 2) Map defender NAMES -> IDs using lineup; if missing, pick reasonable defenders from lineup by team --------
print("Mapping defender names to player_id_clean using lineup...")

def map_names_to_ids(team_name, names):
    ids = []
    team_norm = norm(team_name)
    for n in names:
        key = (team_norm, norm(n))
        pid = lineup_lookup.get(key)
        if pid:
            ids.append(pid)
        else:
            ids.append(None)
    return ids

# For teams where defenders are empty even after JSON extraction, take 2-4 defenders from lineup (prefers category defenders)
# Build team->defender-names from lineup if available
team_defenders_from_lineup = defaultdict(list)
for _, r in lineup.iterrows():
    cat = str(r.get('Category') or r.get('category') or "").lower()
    if 'defender' in cat or 'cover' in cat or 'corner' in cat:
        team_defenders_from_lineup[str(r.get('Team Name') or '').lower().strip()].append(r.get('Player Name') or r.get('Player'))

# Now map
ids_filled = 0
names_filled = 0
for i,row in df.iterrows():
    team = row.get('Opponent_Team_Name') or row.get('Raider_Team_Name') or ""
    names = row['_defs_names'] or []
    if not names:
        # pick up to 3 defenders from lineup for that team (real names)
        picks = team_defenders_from_lineup.get(norm(team), [])[:3]
        if picks:
            df.at[i,'_defs_names'] = picks
            names = picks
            names_filled += 1
    # map to ids
    ids = map_names_to_ids(team, names)
    if any(ids) and all(pid is not None for pid in ids):
        df.at[i,'_defs_ids'] = ids
        ids_filled += 1
    else:
        # if partial mapping, keep mapped values and None for unmapped
        df.at[i,'_defs_ids'] = ids

print("Rows where defender names auto-picked from lineup:", names_filled)
print("Rows where defender ids mapped (complete):", ids_filled)

# -------- 3) Reconcile inconsistent Event_Type vs Event_Outcome --------
print("Reconciling Event_Type vs Event_Outcome inconsistencies...")
def reconcile_event_type_outcome(et, eo, pts):
    et_l = norm(et)
    eo_l = norm(eo)
    # if commentary says unsuccessful but outcome says successful -> likely bonus or overturn
    if 'unsuccess' in et_l and ('success' in eo_l or (pts and float(pts)>0)):
        return "Bonus/Overturn", "bonus"
    # else keep raid type but normalize
    return et, None

df['_reconciled_event_type'] = df['Event_Type']
df['_reconciled_raid_type'] = df['Raid_Type']
count_reconciled = 0
for i,row in df.iterrows():
    new_et, forced_raid = reconcile_event_type_outcome(row['Event_Type'], row['Event_Outcome'], row.get('Score_After'))
    if forced_raid:
        df.at[i,'_reconciled_event_type'] = new_et
        df.at[i,'_reconciled_raid_type'] = "Bonus"
        count_reconciled += 1
print("Rows reconciled as Bonus/Overturn:", count_reconciled)

# -------- 4) Fill missing raider names from player id using lineup if missing --------
print("Filling missing Player_Raider_Name from Player_Raider_ID using lineup...")
id_to_name = {}
for _, r in lineup.iterrows():
    pid = str(r.get('player_id_clean') or "").strip()
    name = r.get('Player Name') or r.get('player_name') or r.get('Player')
    if pid and pd.notna(name):
        name_str = str(name).strip()
        if name_str and name_str.lower() not in ['nan', 'none']:
            id_to_name[pid] = name_str

filled_raider = 0
for i,row in df.iterrows():
    if (not row.get('Player_Raider_Name')) or str(row.get('Player_Raider_Name')).strip() in ['nan','None','']:
        pid = str(row.get('Player_Raider_ID') or "").strip()
        if pid and pid in id_to_name:
            df.at[i,'Player_Raider_Name'] = id_to_name[pid]
            filled_raider += 1
print("Filled missing raider names:", filled_raider)

# -------- 5) Build simplified token column for MDL mining --------
print("Building simplified token column...")
def make_token(r):
    # prefer reconciled raid type if set
    raid = r.get('_reconciled_raid_type') or r.get('Raid_Type') or ""
    eo = r.get('Event_Outcome') or ""
    raid_l = norm(raid)
    # normalize raid tag
    if 'do' in raid_l and 'die' in raid_l: rt = "doordie"
    elif 'bonus' in raid_l: rt = "bonus"
    elif 'empty' in raid_l: rt = "empty"
    elif 'all-out' in raid_l or 'all out' in raid_l: rt = "allout"
    else: rt = "regular"
    # outcome tag
    eo_l = norm(eo)
    if 'succ' in eo_l or 'success' in eo_l:
        out = "success"
    elif 'unsucc' in eo_l or 'fail' in eo_l or 'tackle' in eo_l:
        out = "fail"
    else:
        out = "unknown"
    return f"{rt}_{out}"

df['token'] = df.apply(make_token, axis=1)
df["token"] = df.apply(
    lambda r: f"{r['token']}_{str(r['Raider_Team_Name']).replace(' ', '_')}_vs_{str(r['Opponent_Team_Name']).replace(' ', '_')}",
    axis=1
)

print("Token value counts (top 20):")
print(df['token'].value_counts().head(20).to_string())

# -------- 6) Save result --------
print("Saving preprocessed CSV:", OUTPUT_CSV)
# write defenders back as string lists for compatibility
df['Player_Defenders_Names'] = df['_defs_names'].apply(lambda x: str(x))
df['Player_Defenders_IDs'] = df['_defs_ids'].apply(lambda x: str(x))
# keep important columns and new token
cols_keep = ['Sequence_ID','Season_Number','Match_ID','Match_Phase','Timestamp','Player_Raider_ID','Player_Raider_Name',
             'Raider_Team_ID','Raider_Team_Name','Player_Defenders_IDs','Player_Defenders_Names','Event_Index',
             'Raid_Type','Event_Type','Event_Outcome','Position_Zone','Score_Before','Score_After','Substitution_Info',
             'Opponent_Team_ID','Opponent_Team_Name','token']
df[cols_keep].to_csv(OUTPUT_CSV, index=False)
print("Done.")

