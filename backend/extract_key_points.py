import pandas as pd
from sklearn.preprocessing import MinMaxScaler

try:
    # Load CSVs
    df_contrib = pd.read_csv("player_contribution_stats.csv")
    df_skill = pd.read_csv("player_skill_scores.csv")

    # Standardize key columns before merging
    for df in [df_contrib, df_skill]:
        df["player_name"] = df["player_name"].str.strip().str.lower()
        df["season"] = df["season"].astype(str).str.strip().astype(int)

    # Merge on player_name and season
    merged = pd.merge(df_contrib, df_skill, on=["player_name", "season"], how="inner")

    print(f"✅ Rows after merge: {len(merged)}")

    if merged.empty:
        raise ValueError("Merged DataFrame is empty — check player names or season mismatch between CSVs.")

    # Normalize numeric columns safely
    numeric_cols = [
        "raid_points_player", "tackle_points_player", "total_points",
        "raid_points_contribution", "tackle_points_contribution",
        "do_or_die_points_contribution", "successful_raids_contribution",
        "successful_tackles_contribution", "super_raids_contribution",
        "super_tackles_contribution", "total_skill_score"
    ]

    scaler = MinMaxScaler()
    merged[numeric_cols] = scaler.fit_transform(merged[numeric_cols])

    # Helper functions
    def is_raider(pos):
        return isinstance(pos, str) and "raider" in pos.lower()

    def is_defender(pos):
        return isinstance(pos, str) and "defender" in pos.lower()

    def is_allrounder(pos):
        return isinstance(pos, str) and "all rounder" in pos.lower()

    # Calculate scores
    merged["offense_score"] = (
        0.5 * merged["raid_points_player"] +
        0.2 * merged["raid_points_contribution"] +
        0.1 * merged["do_or_die_points_contribution"] +
        0.1 * merged["successful_raids_contribution"] +
        0.1 * merged["super_raids_contribution"]
    )

    merged.loc[
        merged["position_name_x"].apply(lambda x: is_raider(x) or is_allrounder(x)),
        "offense_score"
    ] += 0.2 * merged["total_skill_score"]

    merged["defense_score"] = (
        0.5 * merged["tackle_points_player"] +
        0.2 * merged["tackle_points_contribution"] +
        0.15 * merged["successful_tackles_contribution"] +
        0.15 * merged["super_tackles_contribution"]
    )

    merged.loc[
        merged["position_name_x"].apply(lambda x: is_defender(x) or is_allrounder(x)),
        "defense_score"
    ] += 0.2 * merged["total_skill_score"]

    merged["overall_score"] = (
        0.4 * merged["offense_score"] +
        0.4 * merged["defense_score"] +
        0.2 * merged["total_points"]
    )
    # Scale scores to 0–100 for easier visualization
    merged["offense_score"] *= 100
    merged["defense_score"] *= 100
    merged["overall_score"] *= 100


    # Aggregate per player
    result = merged.groupby("player_name").agg(
        offense_points=("offense_score", "mean"),
        defense_points=("defense_score", "mean"),
        overall_points=("overall_score", "mean"),
        total_seasons=("season", "nunique"),
        primary_position=("position_name_x", lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0])
    ).reset_index()

    # Capitalize player names again for readability
    result["player_name"] = result["player_name"].str.title()

    # Save to CSV
    result.to_csv("player_effectiveness.csv", index=False)
    print("✅ CSV saved successfully: player_effectiveness.csv")

except FileNotFoundError as e:
    print(f"❌ File not found: {e}")
except KeyError as e:
    print(f"❌ Missing column: {e}")
except Exception as e:
    print(f"⚠️ An error occurred: {e}")
