# diagnostic.py
import pandas as pd
import numpy as np
import re
from ast import literal_eval
from collections import Counter
from datetime import datetime

CSV = "MDL_pattern_dataset_v3_no_season5.csv"   # change if needed
df = pd.read_csv(CSV, dtype=str, low_memory=False)

def info(msg): print("[INFO]", msg)

info(f"Rows, cols: {df.shape}")
info("Columns: " + ", ".join(df.columns.tolist()))

# Basic null counts
info("Null / empty counts for key cols:")
for c in ["Raid_Type","Event_Type","Event_Outcome","Position_Zone","Player_Defenders_Names","Player_Defenders_IDs","Timestamp","Event_Index","Match_ID","Sequence_ID","Player_Raider_Name"]:
    if c in df.columns:
        nulls = df[c].isna().sum() + (df[c].astype(str).str.strip()=="" ).sum()
        info(f"  {c}: {nulls} empty")

# Sequence grouping candidates
for col in ["Sequence_ID","Match_ID","Player_Raider_Name","Raider_Team_Name","Opponent_Team_Name"]:
    if col in df.columns:
        counts = df.groupby(col).size()
        info(f"Grouping by {col}: unique groups={counts.shape[0]}, mean events/group={counts.mean():.2f}, median={counts.median():.0f}, >1 events={(counts>1).sum()}")

# Token diversity (combined token)
def build_token(r):
    parts = []
    for f in ["Raid_Type","Event_Type","Event_Outcome","Position_Zone"]:
        v = r.get(f)
        v = "" if pd.isna(v) else str(v).strip()
        parts.append(v if v!="" else "NA")
    return "|".join(parts)

df['__token'] = df.apply(build_token, axis=1)
tok_counts = df['__token'].value_counts()
info(f"Unique combined tokens: {len(tok_counts)}. Top 20 tokens:\n{tok_counts.head(20).to_string()}")

# Simpler tokens: RaidType_Outcome
def simple_token(r):
    raid = r.get('Raid_Type') or ""
    out = r.get('Event_Outcome') or ""
    raid = str(raid).strip().lower()
    out = str(out).strip().lower()
    # normalize keywords
    if "do" in raid or "do-or-die" in raid: raid_tag = "doordie"
    elif "bonus" in raid: raid_tag = "bonus"
    elif "empty" in raid: raid_tag = "empty"
    else: raid_tag = "regular"
    if "succ" in out or "success" in out or out in ["1","true","successful"]:
        out_tag = "success"
    elif "unsuccess" in out or "fail" in out or out in ["0","false","unsuccessful"]:
        out_tag = "fail"
    else:
        out_tag = "unknown"
    return f"{raid_tag}_{out_tag}"

df['__simp'] = df.apply(simple_token, axis=1)
info("Simplified token counts: " + df['__simp'].value_counts().to_string())

# Inconsistencies: event_type says unsuccessful but event_outcome says success
mask = df['Event_Type'].fillna("").str.lower().str.contains("unsuccess") & df['Event_Outcome'].fillna("").str.lower().str.contains("success")
info(f"Rows where Event_Type contains 'unsuccess' but Event_Outcome contains 'success': {mask.sum()}")
if mask.sum()>0:
    print(df.loc[mask, ['Match_ID','Sequence_ID','Event_Index','Event_Type','Event_Outcome','Raid_Type','Timestamp']].head(10).to_string())

# Defenders missing / malformed
def parse_list(s):
    try:
        L = literal_eval(s)
        if isinstance(L, list): return L
    except:
        pass
    # try simple comma split
    if pd.isna(s): return []
    s = str(s).strip()
    if s=="" or s in ["[]","[None]","['[]']"]: return []
    return [x.strip() for x in re.split(r'[,\|;]', s) if x.strip()]

df['__defs'] = df['Player_Defenders_Names'].apply(parse_list)
df['__defs_id'] = df['Player_Defenders_IDs'].apply(parse_list)
info(f"Rows with no defender names: {(df['__defs'].apply(len)==0).sum()} / {len(df)}")
info(f"Rows with only None IDs: {(df['__defs_id'].apply(lambda x: all([xx in [None,'None',''] for xx in x]) if x else True)).sum()} / {len(df)}")

# Timestamp parsing stats
def to_seconds(ts):
    if pd.isna(ts): return None
    s = str(ts).strip()
    m = re.match(r'^(\d+):(\d{2}):(\d{2})$', s)
    if m: return int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3))
    m = re.match(r'^(\d{1,2}):(\d{2})$', s)
    if m: return int(m.group(1))*60 + int(m.group(2))
    try:
        return int(float(s))
    except:
        return None

df['_ts_sec'] = df['Timestamp'].apply(to_seconds)
info(f"Timestamp parse success: {df['_ts_sec'].notna().sum()} / {len(df)}")
if df['_ts_sec'].notna().sum() > 0:
    print(df.loc[df['_ts_sec'].notna(), ['Match_ID','Sequence_ID','Event_Index','Timestamp']].head(10).to_string())

# Show sample rows where defenders missing but team has players in lineup file (we cannot check lineup here)
info("Sample rows with missing defenders:")
print(df.loc[df['__defs'].apply(len)==0, ['Match_ID','Sequence_ID','Event_Index','Player_Raider_Name','Raider_Team_Name','Opponent_Team_Name','Player_Defenders_Names']].head(20).to_string())
