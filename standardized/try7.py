import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import itertools
import traceback
import json

# Add data loading
csv_path = "MDL_pattern_dataset_v3_no_season5.csv"  # assuming this is the processed dataset
df = pd.read_csv(csv_path, dtype=str)

def simplify_event(row):
    # Focus only on raid success + raid type
    etype = str(row.get('Event_Type', '')).lower()
    outcome = str(row.get('Event_Outcome', '')).lower()
    raid_type = str(row.get('Raid_Type', '')).lower()

    if "raid" not in etype:
        return None  # skip non-raid events

    # normalize categories
    if "successful" in outcome:
        outcome = "success"
    elif "unsuccessful" in outcome or "tackle" in etype:
        outcome = "fail"
    elif "empty" in outcome:
        outcome = "empty"

    raid_tag = ""
    if "do" in raid_type: raid_tag = "DoOrDie"
    elif "super" in raid_type: raid_tag = "Super"
    elif "bonus" in raid_type: raid_tag = "Bonus"
    else: raid_tag = "Normal"

    return f"{raid_tag}_{outcome}"

# Create token column and filter
df['token'] = df.apply(simplify_event, axis=1)
df = df[df['token'].notna()]
print("[DEBUG] After simplifying:", df['token'].value_counts().head(20))

# Save the processed DataFrame to a new CSV file
output_path = "MDL_pattern_dataset_v3_tokenized.csv"
df.to_csv(output_path, index=False)
print(f"\n✅ Processed data saved to: {output_path}")

# then build sequences by Player_Raider_Name
