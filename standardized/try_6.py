import pandas as pd

# === Paths ===
input_path = "MDL_pattern_dataset_v3_grok.csv"
output_path = "MDL_pattern_dataset_v3_no_season5.csv"

# === Load ===
df = pd.read_csv(input_path, dtype=str)

# === Remove Season 5 ===
df = df[df["Season_Number"] != "5"]

# === Save ===
df.to_csv(output_path, index=False)
print(f"✅ Season 5 removed. Saved as: {output_path}")
print(f"Remaining rows: {len(df)}")
