#!/usr/bin/env python3
"""
player_vs_team_insights.py

Produces player-vs-team aggregated metrics and finds frequent patterns (n-grams)
and a simple MDL-like scoring heuristic per (Player_Raider_Name, Opponent_Team_Name).

Outputs:
 - player_vs_team_insights.csv  (one row per raider-opponent pair with top patterns & stats)
 - patterns_<raider>__<opponent>.csv   (optional per-pair frequent n-grams)
"""

import pandas as pd
import numpy as np
import re
import json
from ast import literal_eval
from collections import Counter, defaultdict
from itertools import islice


INPUT_CSV = "MDL_pattern_dataset_preprocessed.csv"
LINEUP_CSV = "Player_Team_Lineup_merged.csv"
OUT_INSIGHTS = "player_vs_team_insights.csv"
MIN_EVENTS_PER_PAIR = 10      # skip pairs with fewer events
TOP_K_PATTERNS = 10
MAX_NGRAM = 4
VERBOSE = True
# --------------------

def info(*a, **k):
    if VERBOSE:
        print("[INFO]", *a, **k)

# --- helpers ---
def parse_list_field(s):
    if pd.isna(s): return []
    ss = str(s).strip()
    if ss in ["", "[]", "[None]", "['[]']", "None"]:
        return []
    try:
        val = literal_eval(ss)
        if isinstance(val, list):
            return [str(x).strip() for x in val if x and str(x).strip() and str(x).strip().lower() not in ['none','nan','[]']]
    except:
        parts = re.split(r'[,\|;]', ss)
        return [p.strip() for p in parts if p.strip() and p.strip().lower() not in ['none','nan','[]']]
    return []

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

def phase_from_seconds(sec):
    if sec is None: return "unknown"
    # crude bins - adjust if you have match duration metadata
    if sec < 20*60: return "early"
    if sec < 40*60: return "mid"
    return "late"



def ngrams(seq, n):
    for i in range(len(seq)-n+1):
        yield tuple(seq[i:i+n])

def frequent_ngrams(sequence_list, n, min_support=2):
    counter = Counter()
    for seq in sequence_list:
        for g in ngrams(seq, n):
            counter[g] += 1
    # return only those with >= min_support
    return counter.most_common()

# Simple MDL-like heuristic (naive): gain = occurrences * (len(pattern)-1) - overhead
def mdl_gain(pattern, occurrences, overhead=1.0):
    # pattern is tuple; naïve bytes saved per occurrence = len(pattern)-1
    return occurrences * (len(pattern)-1) - overhead

def main():
    info("Loading data...")
    df = pd.read_csv(INPUT_CSV, dtype=str, low_memory=False)
    lineup = pd.read_csv(LINEUP_CSV, dtype=str, low_memory=False)

    info("Normalizing and parsing fields...")
    # parse defenders fields to lists
    df['Player_Defenders_Names_list'] = df['Player_Defenders_Names'].apply(parse_list_field)
    df['Player_Defenders_IDs_list'] = df['Player_Defenders_IDs'].apply(parse_list_field)

    # compute raid_points (raider's points for that event) using Score_Before/After
    def safe_int(x):
        try:
            return int(float(x))
        except:
            return None
    df['Score_Before_num'] = df['Score_Before'].apply(safe_int)
    df['Score_After_num'] = df['Score_After'].apply(safe_int)
    df['raid_points'] = df.apply(lambda r: (r['Score_After_num'] - r['Score_Before_num']) if (pd.notna(r['Score_After_num']) and pd.notna(r['Score_Before_num'])) else None, axis=1)

    # timestamp -> seconds and phase
    df['ts_sec'] = df['Timestamp'].apply(to_seconds)
    df['phase'] = df['ts_sec'].apply(phase_from_seconds)

    # build multiple token variants:
    # (A) token_simple: raid_type_outcome (already exists as 'token' but ensure)
    df['token_simple'] = df['token'].astype(str)

    # (B) token_role_phase: include defender role and phase and raid_points bucket
    def score_bucket(p):
        if p is None: return "unk"
        try:
            p = int(p)
            if p >= 2: return "high"
            if p == 1: return "single"
            if p == 0: return "zero"
            if p < 0: return "neg"
        except:
            return "unk"
        return "unk"
    df['raid_pts_bucket'] = df['raid_points'].apply(score_bucket)

    # create token_role_phase
    df['token_role_phase'] = df.apply(lambda r: f"{r['token_simple']}_{r['defender_role']}_{r['phase']}_{r['raid_pts_bucket']}", axis=1)

    info("Built tokens. Sample token_role_phase counts:")
    print(df['token_role_phase'].value_counts().head(20))

    # group by (Player_Raider_Name, Opponent_Team_Name)
    df['Player_Raider_Name'] = df['Player_Raider_Name'].fillna("UNKNOWN_R")
    df['Opponent_Team_Name'] = df['Opponent_Team_Name'].fillna("UNKNOWN_OPP")
    pair_groups = df.groupby(['Player_Raider_Name','Opponent_Team_Name'])
    info(f"Total (raider,opponent) pairs: {len(pair_groups)}")

    results = []
    pair_index = 0
    for (raider, opp), g in pair_groups:
        pair_index += 1
        if pair_index % 200 == 0:
            info("Processed pairs:", pair_index, "so far.")
        g = g.sort_values(['Match_ID','Event_Index'], na_position='last')
        n_events = len(g)
        if n_events < MIN_EVENTS_PER_PAIR:
            continue

        # sequence for this pair (we'll use token_role_phase for more informative patterns)
        seq = g['token_role_phase'].tolist()
        seq_simple = g['token_simple'].tolist()

        # basic stats
        total_raids = n_events
        succ_cnt = g['Event_Outcome'].str.lower().str.contains('succ').sum()
        avg_points = g['raid_points'].dropna().astype(float).mean() if g['raid_points'].dropna().shape[0] else 0.0
        doordie_success = g[g['token_simple'].str.contains('doordie') & g['Event_Outcome'].str.lower().str.contains('succ')].shape[0]
        bonus_success = g[g['token_simple'].str.contains('bonus') & g['Event_Outcome'].str.lower().str.contains('succ')].shape[0]

        # frequent n-grams (simple count)
        all_counts = Counter()
        for n in range(1, MAX_NGRAM+1):
            for ng, cnt in Counter(ngr for ngr in ngrams(seq, n)).items():
                all_counts[ng] += cnt

        # top patterns by freq
        top_patterns = all_counts.most_common(TOP_K_PATTERNS)

        # naive MDL-like scoring: compute occurrences of each pattern across the single seq (we treat seq as one long sequence for the pair)
        # For multi-sequence MDL you'd need occurrences across many sequences; here we attempt per-pair motif extraction.
        scored = []
        for pattern, occ in top_patterns:
            # compute naive gain
            gain = mdl_gain(pattern, occ, overhead=1.0)
            scored.append((pattern, occ, gain))
        scored_sorted = sorted(scored, key=lambda x: x[2], reverse=True)

        # Save a small CSV of top patterns per pair (optional)
        try:
            safe_raider = re.sub(r'[^A-Za-z0-9]+', '_', raider)[:50]
            safe_opp = re.sub(r'[^A-Za-z0-9]+', '_', opp)[:50]
            small_name = f"patterns_{safe_raider}__{safe_opp}.csv"
            outp = pd.DataFrame([{"pattern":"||".join(pat), "support":sup, "gain":gain} for pat,sup,gain in scored_sorted])
            outp.to_csv(small_name, index=False)
        except Exception as e:
            pass

        # prepare top-n human readable summary
        top_read = []
        for pat, sup, gain in scored_sorted[:5]:
            top_read.append({"pattern":" > ".join(pat), "support":sup, "gain":gain})

        results.append({
            "raider": raider,
            "opponent": opp,
            "n_events": total_raids,
            "success_rate": float(succ_cnt)/total_raids if total_raids else 0.0,
            "avg_points_per_raid": float(avg_points) if avg_points is not None else 0.0,
            "doordie_success_count": int(doordie_success),
            "bonus_success_count": int(bonus_success),
            "top_patterns": json.dumps(top_read, ensure_ascii=False)
        })

    # write results
    info("Writing final insights CSV:", OUT_INSIGHTS)
    outdf = pd.DataFrame(results)
    if outdf.shape[0]==0:
        info("No (raider,opponent) pairs met MIN_EVENTS_PER_PAIR threshold. Try lowering MIN_EVENTS_PER_PAIR.")
    outdf.to_csv(OUT_INSIGHTS, index=False)
    info("Done. Wrote", OUT_INSIGHTS)

if __name__ == "__main__":
    main()
