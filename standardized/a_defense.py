import pandas as pd
import itertools
import json
from collections import Counter, defaultdict
import traceback

DATA_PATH = "MDL_pattern_dataset_preprocessed.csv"
OUTPUT_DIR = "defense_patterns/"
MIN_SUPPORT = 5  # Minimum times a pattern must appear
TOP_N_TRANSITIONS = 30



def debug(msg):
    print(f"[DEBUG] {msg}")


def simplify_defense_event(row):
    """
    Converts each event into a simplified defense token.
    """
    raid_type = str(row.get("Raid_Type", "")).lower()
    etype = str(row.get("Event_Type", "")).lower()
    outcome = str(row.get("Event_Outcome", "")).lower()

    if "tackle" in etype or "unsuccessful" in etype or "tackle" in outcome:
        result = "tackle_success" if "unsuccessful" in outcome else "tackle_fail"
    elif "super" in raid_type:
        result = "super_tackle_success" if "unsuccessful" in outcome else "super_tackle_fail"
    else:
        result = "defense_unknown"

    raid_tag = ""
    if "do" in raid_type:
        raid_tag = "doordie"
    elif "super" in raid_type:
        raid_tag = "super"
    elif "bonus" in raid_type:
        raid_tag = "bonus"
    else:
        raid_tag = "regular"

    token = f"{raid_tag}_{result}"
    return token


def build_defense_sequences(df):
    """
    Explodes defender lists and builds defender-centered sequences.
    """
    debug("Exploding defenders and building defense sequences...")

    df["token_def"] = df.apply(simplify_defense_event, axis=1)

    # Ensure list format
    df["Player_Defenders_Names"] = df["Player_Defenders_Names"].apply(
        lambda x: eval(x) if isinstance(x, str) and x.startswith("[") else [x]
    )

    df_exploded = df.explode("Player_Defenders_Names").dropna(subset=["Player_Defenders_Names"])
    debug(f"Exploded defender rows: {len(df_exploded)}")

    grouped = defaultdict(list)
    for _, row in df_exploded.iterrows():
        defender = row["Player_Defenders_Names"]
        token = f"{row['token_def']}_{row['Raider_Team_Name']}_vs_{row['Opponent_Team_Name']}"
        grouped[defender].append(token)

    debug(f"Built {len(grouped)} defender sequences.")
    return grouped


def mine_frequent_transitions(sequences, min_support=MIN_SUPPORT):
    """
    Simple n-gram frequency counter for patterns.
    """
    transitions = Counter()

    for seq in sequences.values():
        for a, b in zip(seq, seq[1:]):
            transitions[(a, b)] += 1

    # Filter
    frequent = {k: v for k, v in transitions.items() if v >= min_support}
    return frequent


def save_patterns(defender_name, transitions):
    """
    Save transitions for a single defender to CSV.
    """
    df = pd.DataFrame(
        [(k[0], k[1], v) for k, v in transitions.items()],
        columns=["From_Token", "To_Token", "Support"]
    ).sort_values(by="Support", ascending=False)

    fname = f"{OUTPUT_DIR}patterns_{defender_name.replace(' ', '_')}.csv"
    df.to_csv(fname, index=False)
    debug(f"Saved defender patterns: {fname} ({len(df)} transitions)")


def run_defense_pipeline():
    try:
        debug("=== Starting Defense MDL pipeline ===")

        df = pd.read_csv(DATA_PATH)
        debug(f"Loaded dataframe: {df.shape[0]} rows, {df.shape[1]} cols")

        sequences = build_defense_sequences(df)
        all_transitions = {}

        for defender, seq in sequences.items():
            if len(seq) < 3:
                continue
            trans = mine_frequent_transitions({defender: seq})
            if not trans:
                continue
            all_transitions[defender] = trans
            save_patterns(defender, trans)

        # Aggregate summary
        summary_rows = []
        for defender, trans in all_transitions.items():
            total_patterns = len(trans)
            total_support = sum(trans.values())
            summary_rows.append((defender, total_patterns, total_support))

        summary_df = pd.DataFrame(summary_rows, columns=["Defender", "Num_Patterns", "Total_Support"])
        summary_df.to_csv(f"{OUTPUT_DIR}defense_summary.csv", index=False)
        debug(f"Saved overall summary: {OUTPUT_DIR}defense_summary.csv")

        debug("=== Defense MDL pipeline completed ===")

    except Exception as e:
        debug(f"Fatal error in defense pipeline: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    run_defense_pipeline()
