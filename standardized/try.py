# import zipfile, json, re, os
# import pandas as pd
# from collections import defaultdict

# # === File paths (adjust these) ===
# zip_path = "prokabaddi_commentary_season5plus.zip"
# csv_path = "Player_Team_Lineup_merged.csv"
# out_csv = "MDL_pattern_dataset_v2.csv"

# # === Team mapping (your given key pairs) ===
# team_map = {
#     "bengaluru bulls": 1,
#     "dabang delhi": 2, "dabang delhi k.c.": 2,
#     "jaipur pink panthers": 3,
#     "bengal warriors": 4,
#     "u mumba": 5, "u. mumba": 5, "umumba": 5,
#     "patna pirates": 6,
#     "puneri paltan": 7,
#     "telugu titans": 8,
#     "haryana steelers": 28,
#     "tamil thalaivas": 29,
#     "u.p. yoddhas": 30, "up yoddhas": 30,
#     "gujarat giants": 31, "gujarat fortunegiants": 31
# }

# def map_team_name_to_id(team_name):
#     if not team_name:
#         return None
#     name = team_name.lower().strip()
#     for key in team_map:
#         if key in name or name in key:
#             return team_map[key]
#     return None


# # === Load lineup ===
# players = pd.read_csv(csv_path, dtype=str)
# players['player_name_norm'] = players['Player Name'].fillna('').str.lower().str.strip()
# players['team_name_norm'] = players['Team Name'].fillna('').str.lower().str.strip()

# by_season_team_player = {}
# by_name = defaultdict(list)

# for _, r in players.iterrows():
#     season = r.get('season_num')
#     teamn = r.get('team_name_norm')
#     pname = r.get('player_name_norm')
#     key = (season, teamn, pname)
#     by_season_team_player[key] = r.to_dict()
#     by_name[pname].append(r.to_dict())

# # === Load match JSON ===
# z = zipfile.ZipFile(zip_path)
# data = json.load(z.open(z.namelist()[0]))

# records = []

# for season_entry in data:
#     season_field = season_entry.get('season', '')
#     m = re.search(r'(\d+)', str(season_field))
#     season_num = str(int(m.group(1))) if m else None

#     for match in season_entry.get('matches', []):
#         match_id = match.get('match_id')
#         team_a = match.get('team_a', {}).get('name')
#         team_b = match.get('team_b', {}).get('name')
#         team_a_id = map_team_name_to_id(team_a)
#         team_b_id = map_team_name_to_id(team_b)

#         scores = {team_a: 0, team_b: 0}

#         for idx, ev in enumerate(match.get('events', [])):
#             event_index = idx + 1
#             sequence_id = f"{match_id}_R{event_index}"

#             # Extract basic info
#             half = ev.get('half')
#             timestamp = ev.get('time')
#             event_type = ev.get('event_type')
#             raider_name = ev.get('raider')
#             tackled_by = ev.get('tackled_by')
#             defenders = []

#             if tackled_by:
#                 if isinstance(tackled_by, list):
#                     defenders = [x.strip() for x in tackled_by if x]
#                 elif isinstance(tackled_by, str) and "," in tackled_by:
#                     defenders = [x.strip() for x in tackled_by.split(",")]
#                 else:
#                     defenders = [str(tackled_by).strip()]

#             # Raider mapping
#             raider_id = None
#             raider_team_id = None
#             raider_team_name = None
#             raider_name_norm = str(raider_name).lower().strip() if raider_name else None

#             if raider_name_norm:
#                 for tname in [team_a, team_b]:
#                     key = (season_num, tname.lower().strip() if tname else None, raider_name_norm)
#                     if key in by_season_team_player:
#                         info = by_season_team_player[key]
#                         raider_id = info.get('player_id_clean')
#                         raider_team_id = info.get('team_id')
#                         raider_team_name = info.get('Team Name')
#                         break

#                 if raider_id is None and raider_name_norm in by_name:
#                     info = by_name[raider_name_norm][0]
#                     raider_id = info.get('player_id_clean')
#                     raider_team_id = info.get('team_id')
#                     raider_team_name = info.get('Team Name')

#             # Defender mapping
#             defender_ids = []
#             defender_names = []
#             for d in defenders:
#                 dn = d.lower()
#                 defender_names.append(d)
#                 if dn in by_name and by_name[dn]:
#                     defender_ids.append(by_name[dn][0].get('player_id_clean'))
#                 else:
#                     defender_ids.append(None)

#             # Raid Type (directly from JSON)
#             raid_type = None
#             if ev.get('do_or_die'):
#                 raid_type = "Do-or-Die"
#             elif ev.get('all_out'):
#                 raid_type = "All-Out"
#             else:
#                 if event_type:
#                     et = event_type.lower()
#                     if "bonus" in et: raid_type = "Bonus"
#                     elif "super" in et: raid_type = "Super"
#                     elif "empty" in et: raid_type = "Empty"
#                     else: raid_type = event_type

#             # Event outcome inference
#             desc = (ev.get('description') or "").lower()
#             pts = ev.get('points') or 0
#             outcome = "Successful" if pts > 0 or "successful" in desc else "Unsuccessful" if "unsuccessful" in desc or "tackle" in desc else "Empty"

#             # Score tracking
#             team_of_raider = raider_team_name or team_a
#             score_before = scores.get(team_of_raider, 0)
#             score_after = score_before + (pts if isinstance(pts, (int, float)) else 0)
#             scores[team_of_raider] = score_after

#             # Opponent mapping
#             if team_of_raider and team_a and team_b:
#                 if team_of_raider.lower().strip() == team_a.lower().strip():
#                     opponent_team_name, opponent_team_id = team_b, team_b_id
#                 else:
#                     opponent_team_name, opponent_team_id = team_a, team_a_id
#             else:
#                 opponent_team_name, opponent_team_id = team_b, team_b_id

#             records.append({
#                 "Sequence_ID": sequence_id,
#                 "Season_Number": season_num,
#                 "Match_ID": match_id,
#                 "Match_Phase": half,
#                 "Timestamp": timestamp,
#                 "Player_Raider_ID": raider_id,
#                 "Player_Raider_Name": raider_name,
#                 "Raider_Team_ID": raider_team_id,
#                 "Raider_Team_Name": raider_team_name,
#                 "Player_Defenders_IDs": str(defender_ids),
#                 "Player_Defenders_Names": str(defender_names),
#                 "Event_Index": event_index,
#                 "Raid_Type": raid_type,
#                 "Event_Type": event_type,
#                 "Event_Outcome": outcome,
#                 "Position_Zone": None,
#                 "Score_Before": score_before,
#                 "Score_After": score_after,
#                 "Substitution_Info": json.dumps(ev.get('substitution')) if ev.get('substitution') else "",
#                 "Opponent_Team_ID": opponent_team_id,
#                 "Opponent_Team_Name": opponent_team_name
#             })

# # === Export to CSV ===
# df = pd.DataFrame(records)
# df.to_csv(out_csv, index=False)
# print(f"✅ Dataset created: {out_csv}")
# print(f"Total events: {len(df)}")
import os
import re
import sys

folder = r"PlayerRaids"

if not os.path.isdir(folder):
    print(f"Folder not found: {folder}")
    sys.exit(1)

for filename in os.listdir(folder):
    # only process CSV files starting with patterns_
    if not (filename.startswith("patterns_") and filename.lower().endswith(".csv")):
        continue

    old_path = os.path.join(folder, filename)

    # normalize name: collapse repeated underscores, replace spaces, unify team name
    new_name = re.sub(r'__+', '__', filename)
    new_name = new_name.replace(" ", "_")
    # unify "Yoddhas" -> "Yoddha" (case-insensitive)
    new_name = re.sub(r'(?i)Yoddhas', 'Yoddha', new_name)

    new_path = os.path.join(folder, new_name)

    # if identical, skip
    if os.path.abspath(old_path) == os.path.abspath(new_path):
        continue

    # avoid overwriting existing file: append suffix if needed
    if os.path.exists(new_path):
        base, ext = os.path.splitext(new_name)
        i = 1
        while True:
            candidate = f"{base}_{i}{ext}"
            candidate_path = os.path.join(folder, candidate)
            if not os.path.exists(candidate_path):
                new_name = candidate
                new_path = candidate_path
                break
            i += 1

    try:
        os.rename(old_path, new_path)
        print(f"Renamed: {filename} -> {new_name}")
    except Exception as e:
        print(f"Failed to rename {filename}: {e}")