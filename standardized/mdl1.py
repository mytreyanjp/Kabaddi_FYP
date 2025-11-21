"""
Debug-enabled MDL-style pattern miner for Kabaddi.
Prints detailed progress info to help identify where errors occur.
"""

import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import itertools
import traceback
import json
import sys
# === USER PARAMETERS ===
DATA_PATH = sys.argv[1] if len(sys.argv) > 1 else "MDL_pattern_dataset_preprocessed.csv"
OUTPUT_PATTERNS = "discovered_patterns_debug.json"
MIN_SUPPORT = 2
MAX_PATTERN_LEN = 4
OVERHEAD_COST_COEFF = 0.8
COMBINE_FIELDS = ["token"]
SEQUENCE_COL = "Match_ID"
print("SEQUENCE_COL",SEQUENCE_COL)
ORDER_COL = "Event_Index"
TOKEN_COL = "token"
FILTER_CONSTRAINTS = {}

# === Utility Functions ===

def debug(msg):
    print(f"[DEBUG] {msg}")

def build_token(row, fields):
    parts = []
    for f in fields:
        v = row.get(f, None)
        if pd.isna(v) or v is None:
            parts.append("NA")
        else:
            parts.append(str(v).strip())
    return "|".join(parts)

def load_and_preprocess(path):
    try:
        debug(f"Loading CSV: {path}")
        df = pd.read_csv(path, dtype=str, low_memory=False)
        debug(f"Loaded dataframe: {df.shape[0]} rows, {df.shape[1]} cols")
        debug(f"Columns: {list(df.columns)}")

        # apply optional constraints
        if FILTER_CONSTRAINTS:
            debug(f"Applying constraints: {FILTER_CONSTRAINTS}")
            for k, v in FILTER_CONSTRAINTS.items():
                if k in df.columns:
                    before = len(df)
                    df = df[df[k].astype(str).str.lower() == str(v).lower()]
                    debug(f"Filtered {k}={v}: {before} -> {len(df)} rows")

        if ORDER_COL in df.columns:
            df[ORDER_COL] = pd.to_numeric(df[ORDER_COL], errors="coerce").fillna(0).astype(int)
            df = df.sort_values([SEQUENCE_COL, ORDER_COL])
        else:
            df = df.sort_values(SEQUENCE_COL)

        sequences = defaultdict(list)
        meta = defaultdict(list)
        for i, row in df.iterrows():
            seqid = row.get(SEQUENCE_COL)
            if pd.isna(seqid):
                continue
            token = build_token(row, COMBINE_FIELDS)
            sequences[seqid].append(token)
            meta[seqid].append(row.to_dict())

        debug(f"Built {len(sequences)} sequences.")
        sample_keys = list(sequences.keys())[:3]
        for sk in sample_keys:
            debug(f"Sample Sequence {sk}: {sequences[sk][:5]} ...")
        return sequences, meta

    except Exception as e:
        debug(f"Error in load_and_preprocess: {e}")
        traceback.print_exc()
        raise

def find_frequent_single_tokens(sequences, min_support):
    counts = Counter()
    for seq in sequences.values():
        counts.update(set(seq))
    return {t:c for t,c in counts.items() if c >= min_support}

def candidate_generation(prev_patterns, k):
    candidates = set()
    for a in prev_patterns:
        for b in prev_patterns:
            if a[1:] == b[:-1]:
                candidates.add(a + (b[-1],))
    return [tuple(c) for c in candidates]

def count_pattern_support(pattern, sequences):
    patlen = len(pattern)
    occ = []
    for sid, seq in sequences.items():
        positions = []
        for i in range(len(seq) - patlen + 1):
            if seq[i:i+patlen] == list(pattern):
                positions.append(i)
        if positions:
            occ.append((sid, positions))
    return len(occ), occ

def pattern_cost_overhead(pattern_len, overhead_coeff):
    return overhead_coeff * pattern_len

def pattern_savings(pattern_len, support):
    return support * (pattern_len - 1)

def pattern_gain(pattern_len, support, overhead_coeff):
    return pattern_savings(pattern_len, support) - pattern_cost_overhead(pattern_len, overhead_coeff)

def greedy_mdl_extract(sequences):
    debug("Starting greedy MDL extraction")
    avg_len = np.mean([len(s) for s in sequences.values()])
    debug(f"Average sequence length: {avg_len:.2f}")

    one_freq = find_frequent_single_tokens(sequences, MIN_SUPPORT)
    debug(f"Found {len(one_freq)} frequent 1-tokens")

    discovered = []
    sequences_work = {k: list(v) for k, v in sequences.items()}

    try:
        for L in range(1, MAX_PATTERN_LEN + 1):
            debug(f"--- Iteration L={L} ---")

            if L == 1:
                pattern_tuples = [ (t,) for t in one_freq.keys() ]
            else:
                prev_patterns = [tuple(p['pattern']) for p in discovered if len(p['pattern']) == L - 1]
                pattern_tuples = candidate_generation(prev_patterns, L)

            debug(f"Generated {len(pattern_tuples)} candidates of length {L}")

            for pat in pattern_tuples:
                support, occ = count_pattern_support(pat, sequences_work)
                if support >= MIN_SUPPORT:
                    gain = pattern_gain(len(pat), support, OVERHEAD_COST_COEFF)
                    if gain > 0:
                        discovered.append({
                            "pattern": list(pat),
                            "length": len(pat),
                            "support": support,
                            "gain": gain,
                        })
                        debug(f"Accepted pattern {pat}, support={support}, gain={gain:.2f}")
            debug(f"Total discovered so far: {len(discovered)}")

    except Exception as e:
        debug(f"Error in greedy_mdl_extract: {e}")
        traceback.print_exc()
        raise

    discovered.sort(key=lambda x: -x["gain"])
    debug(f"Finished MDL extraction with {len(discovered)} patterns.")
    return discovered, sequences_work

def run_mdl_pipeline():
    debug("=== Starting MDL pipeline ===")
    try:
        sequences, meta = load_and_preprocess(DATA_PATH)
        debug("Preprocessing done, running pattern extraction...")
        pair_counter = Counter()
        for seq in sequences.values():
            for i in range(len(seq) - 1):
                pair = (seq[i], seq[i+1])
                pair_counter[pair] += 1
        print("[DEBUG] Top 20 frequent 2-token transitions:")
        for p, c in pair_counter.most_common(20):
            print(f"{p}: {c}")
        discovered, rewritten = greedy_mdl_extract(sequences)
        debug(f"Discovered {len(discovered)} patterns in total")

        # Save results
        with open(OUTPUT_PATTERNS, "w", encoding="utf-8") as f:
            json.dump(discovered, f, indent=2, ensure_ascii=False)
        debug(f"Patterns saved to {OUTPUT_PATTERNS}")
        print("Top 5 patterns:")
        for p in discovered[:5]:
            print(p)
        debug("=== MDL pipeline completed ===")

    except Exception as e:
        debug(f"Fatal error in pipeline: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run_mdl_pipeline(

    )
