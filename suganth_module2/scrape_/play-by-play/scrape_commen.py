from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re
import json
import os


# 🧩 1. Create Chrome driver
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    return webdriver.Chrome(options=chrome_options)


# 🧩 2. Build player → team map
def build_player_team_map(soup):
    player_team_map = {}
    team_boxes = soup.select("div.team-box")
    for team_box in team_boxes:
        team_name_elem = team_box.select_one(".team-name, .teamTitle")
        if not team_name_elem:
            continue
        team_name = team_name_elem.get_text(strip=True)
        player_elems = team_box.select(".player-list .player, .player-list .player-name, .player-name")
        for player_elem in player_elems:
            pname = player_elem.get_text(strip=True)
            if pname:
                player_team_map[pname.strip().lower()] = team_name
    return player_team_map


# 🧩 3. Parse one commentary event
def parse_event_from_commentary_section(block, player_team_map):
    half, minute, raider, event_type, tackled_by, team = None, None, None, None, None, None
    players_out, do_or_die, all_out = [], False, False
    substitution = {}

    # Timer (Half + Time)
    timer_div = block.select_one("div.body div.timer span.timer-text")
    if timer_div:
        txt = "".join(timer_div.stripped_strings)
        match = re.match(r"(\d+).+Half: ?(\d+)'", txt)
        if match:
            half = f"{match.group(1)} Half"
            minute = match.group(2)

    # Event type and flags
    points_header = block.select_one("div.match-commentary div.commentary-data div.points-history div.points-header")
    event_type = ""
    if points_header:
        label = points_header.select_one("span.label")
        title = points_header.select_one("span.title")
        label_text = label.get_text(strip=True) if label else ""
        title_text = title.get_text(strip=True) if title else ""
        if label_text:
            event_type = label_text
        elif title_text:
            event_type = title_text

        for sub in points_header.find_all("span", class_="sub-title"):
            if "do or die" in sub.text.lower(): do_or_die = True
            if "all out" in sub.text.lower(): all_out = True

    # Extract players and team info
    data_blocks = block.select("div.match-commentary div.commentary-data")
    if data_blocks:
        for cdata in data_blocks:
            for info in cdata.select("div.points-history div.points-information"):
                label = info.select_one("span.label")
                label_text = (
                    label.get_text(strip=True)
                    .lower()
                    .replace(":", "")
                    .replace("\xa0", "")
                    .strip()
                    if label else ""
                )

                player_elems = info.select("span.player-name")
                player_text = ", ".join([p.get_text(strip=True) for p in player_elems if p.get_text(strip=True)]) if player_elems else ""

                if "raider" in label_text:
                    raider = player_text
                elif "players out" in label_text or "player out" in label_text:
                    players_out.extend([x.strip() for x in player_text.split(",") if x.strip()])
                elif "tackled by" in label_text:
                    tackled_by = player_text
                elif label_text == "in":
                    substitution["in"] = player_text
                elif label_text == "out":
                    substitution["out"] = player_text

        if raider and player_team_map:
            team = player_team_map.get(raider.strip().lower())

    # Points logic
    points = len(players_out) if event_type and event_type.lower() == "successful raid" else 0
    if event_type and event_type.lower() == "successful raid" and not players_out:
        points = 1

    # Description
    if event_type and "substitution" in event_type.lower() and substitution.get("in") and substitution.get("out"):
        desc = f"Substitution: In: {substitution['in']}; Out: {substitution['out']}."
    elif event_type and event_type.lower() == "successful raid" and raider:
        desc = f"{raider} executes a successful raid"
        desc += f", getting {' and '.join(players_out)} out." if players_out else "."
    elif event_type and event_type.lower() == "unsuccessful raid" and raider and tackled_by:
        desc = f"{raider} is tackled by {tackled_by} on an unsuccessful raid."
    elif event_type and event_type.lower() == "empty raid" and raider:
        desc = f"{raider} makes an empty raid."
    elif event_type in ["Timeout", "Toss"]:
        desc = event_type
    else:
        desc = block.get_text(" ", strip=True)

    event_json = {
        "half": half,
        "time": minute,
        "event_type": event_type,
        "raider": raider,
        "team": team,
        "players_out": players_out,
        "tackled_by": tackled_by,
        "do_or_die": do_or_die,
        "all_out": all_out,
        "substitution": substitution if substitution else None,
        "points": points,
        "description": desc
    }
    return event_json


# 🧩 4. Extract commentary from URL
def kabaddi_commentary_from_url(match_url):
    driver = create_driver()
    print(f"  🔗 Fetching: {match_url}")
    driver.get(match_url)
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "playbyplay-section")))
    except:
        print("  ⚠️ No play-by-play section found.")
        driver.quit()
        return []

    time.sleep(2)
    for _ in range(12):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.8)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    player_team_map = build_player_team_map(soup)
    playbyplay_section = soup.select_one("div.playbyplay-section")
    events = []

    if playbyplay_section:
        commentary_blocks = playbyplay_section.select("div.commentary-section")
        print(f"   📜 Found {len(commentary_blocks)} commentary-section blocks")
        for idx, blk in enumerate(commentary_blocks, 1):
            event_json = parse_event_from_commentary_section(blk, player_team_map)
            if event_json["event_type"]:
                print(f"     ✅ Event {idx}: {event_json['event_type']} ({event_json['description'][:60]}...)")
                events.append(event_json)

    if not events:
        print("  ⚠️ No commentary events found.")
    return events


# 🧩 5. Loop through matches (Season 5 onward)
def scrape_season_commentary(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        all_data = json.load(f)

    output = []
    for season_data in all_data:
        season_name = season_data.get("season")
        if not season_name or not season_name.startswith("Season"):
            continue
        season_num = int(season_name.split()[-1])
        if season_num < 5:
            continue

        print(f"\n==============================")
        print(f"🏆 Scraping {season_name}")
        print("==============================")

        season_output = {"season": season_name, "matches": []}
        for match in season_data.get("matches", []):
            match_id = match.get("match_id")
            match_url = match.get("match_url")
            print(f"\n🔹 Match ID: {match_id}")
            print(f"   URL: {match_url}")

            events = kabaddi_commentary_from_url(match_url)
            match_entry = {
                "match_id": match_id,
                "match_url": match_url,
                "team_a": match.get("team_a"),
                "team_b": match.get("team_b"),
                "status": match.get("status"),
                "events": events
            }
            season_output["matches"].append(match_entry)

        output.append(season_output)

    os.makedirs("commentary_output", exist_ok=True)
    with open("commentary_output/prokabaddi_commentary_season5plus.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n✅ All seasons (5+) scraped and saved in commentary_output/prokabaddi_commentary_season5plus.json")


# 🧩 6. Run script
if __name__ == "__main__":
    scrape_season_commentary("prokabaddi_matches.json")
