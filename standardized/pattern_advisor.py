import os
import pandas as pd

# === CONFIG ===
PATTERNS_FOLDER = "./PlayerRaids"  # folder containing all patterns_*.csv
OUTPUT_FOLDER = "./reports/"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def interpret_token(token: str):

    parts = token.split("_vs_")
    if len(parts) != 2:
        return {"raid_type": "unknown", "team": "unknown", "opponent": "unknown"}

    left, right = parts
    left_parts = left.split("_")
    raid_type = left_parts[0] if len(left_parts) > 0 else "unknown"
    outcome = left_parts[1] if len(left_parts) > 1 else "unknown"
    team = "_".join(left_parts[2:]) if len(left_parts) > 2 else "unknown"
    opponent = right.split("_")[0]
    return {"raid_type": raid_type, "outcome": outcome, "team": team, "opponent": opponent}


def infer_meaning(row):

    pattern = row["pattern"]
    support = row["support"]
    gain = row["gain"]

    tokens = pattern.split("||")
    parts = [interpret_token(t) for t in tokens]

    # Short pattern summaries
    desc = []
    for p in parts:
        rt, oc = p["raid_type"], p["outcome"]
        if rt == "doordie":
            desc.append(f"Do-or-Die raid ({oc})")
        elif rt == "bonus":
            desc.append(f"Bonus attempt ({oc})")
        elif rt == "regular":
            desc.append(f"Regular raid ({oc})")
        elif rt == "empty":
            desc.append(f"Empty raid ({oc})")
        elif rt == "allout":
            desc.append(f"All-Out phase ({oc})")
        else:
            desc.append(f"Other raid ({oc})")

    description = " → ".join(desc)

    # Interpret pattern impact
    if gain > 0:
        sentiment = "frequent and advantageous"
    elif gain == -1:
        sentiment = "common but low-impact"
    else:
        sentiment = "uncommon or neutral"

    if "success" in pattern:
        implication = "positive scoring tendency"
    elif "unknown" in pattern or "empty" in pattern:
        implication = "neutral or non-scoring trend"
    else:
        implication = "negative scoring trend"

    return {
        "Pattern": description,
        "Support": support,
        "Gain": gain,
        "Summary": f"This pattern ({description}) occurs {support} times and represents a {sentiment} behavior ({implication})."
    }


def generate_advice(df, player, team):

    success_patterns = df[df["pattern"].str.contains("success")]
    unknown_patterns = df[df["pattern"].str.contains("unknown|empty")]
    bonus_patterns = df[df["pattern"].str.contains("bonus")]
    doordie_patterns = df[df["pattern"].str.contains("doordie")]

    report = []
    report.append(f"### Tactical Report for {player} vs {team}\n")
    report.append(f"**Total Patterns Analyzed:** {len(df)}\n")

    if len(doordie_patterns) > 0:
        report.append(f"- {player} frequently engages in Do-or-Die raids — useful for high-pressure moments.")
    if len(bonus_patterns) > 0:
        report.append(f"- Bonus attempts are part of {player}'s strategy — can exploit weak corners or single defenders.")
    if len(unknown_patterns) > 10:
        report.append(f"- Several non-scoring or unclear raids detected — potential inefficiency or defensive strength from {team}.")
    if len(success_patterns) > len(unknown_patterns):
        report.append(f"- Higher success ratio suggests {player} performs effectively against {team}.")
    else:
        report.append(f"- Lower success ratio suggests {player} struggles to convert raids against {team}’s defense.")

    report.append("\n### Recommendations:\n")
    if len(doordie_patterns) > len(unknown_patterns):
        report.append("Use in Do-or-Die situations for momentum shifts.")
    else:
        report.append("Avoid excessive Do-or-Die raids; defense adapts quickly.")
    if len(bonus_patterns) > 0:
        report.append(" Encourage bonus attempts early in the raid clock.")
    if len(unknown_patterns) > len(success_patterns):
        report.append("Review defensive setups; too many non-scoring attempts.")

    return "\n".join(report)


def process_all_patterns():
    files = [f for f in os.listdir(PATTERNS_FOLDER) if f.startswith("patterns_") and f.endswith(".csv")]
    for file in files:
        try:
            path = os.path.join(PATTERNS_FOLDER, file)
            df = pd.read_csv(path)
            if df.empty:
                continue

            # Infer player and team names
            name = file.replace("patterns_", "").replace(".csv", "")
            parts = name.split("__")
            player = parts[0].replace("_", " ")
            team = parts[1].replace("_", " ") if len(parts) > 1 else "Unknown"

            # Interpret each pattern
            interpreted = df.apply(infer_meaning, axis=1, result_type="expand")

            # Generate tactical advice
            summary = generate_advice(df, player, team)

            # Save readable report
            output_text = f"# Tactical Insights for {player} vs {team}\n\n"
            output_text += summary + "\n\n---\n\n"
            output_text += interpreted[["Pattern", "Support", "Gain", "Summary"]].to_markdown(index=False)

            with open(os.path.join(OUTPUT_FOLDER, f"{name}_report.md"), "w", encoding="utf-8") as f:
                f.write(output_text)

            print(f"[INFO] Generated  report for {player} vs {team}")
        except Exception as e:
            print(f"[ERROR] Failed {file}: {e}")


if __name__ == "__main__":
    process_all_patterns()
