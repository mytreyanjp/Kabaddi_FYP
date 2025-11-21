import json
from collections import defaultdict
from demo_lib import scrape_match  # your function from demo.py or demo_lib.py

# Load all matches (list of season objects)
with open("../all_match_data/prokabaddi_matches.json", "r", encoding="utf-8") as f:
    data = json.load(f)

season_wise = defaultdict(list)

# 🔹 Filter only Season 1
for season_data in data:
    season_name = season_data.get("season", "Unknown_Season")
    if season_name.strip().lower() != "season 1":
        continue  # skip all other seasons

    matches = season_data.get("matches", [])
    print(f"\n🎯 Starting scraping for {season_name} ({len(matches)} matches)...\n")

    for match in matches:
        match_id = match.get("match_id")
        match_url = match.get("match_url")

        if not match_url or not isinstance(match_url, str):
            print(f"⚠️ Skipping match {match_id} in {season_name} — invalid or missing URL")
            continue

        print(f"🕵️ Scraping Match {match_id} ({season_name}) ...")
        try:
            result = scrape_match(match_url, match_id)
            season_wise[season_name].append(result)
        except Exception as e:
            print(f"❌ Failed to scrape {match_id} ({season_name}): {e}")

# 🔹 Save results for Season 1 only
for season, matches in season_wise.items():
    filename = f"{season.replace(' ', '_')}_matches.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(matches)} matches for {season} → {filename}")
