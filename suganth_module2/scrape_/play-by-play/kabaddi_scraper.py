"""
kabaddi_commentary.py
---------------------------------
A reusable library for scraping Pro Kabaddi match commentary data.

Usage:
    from kabaddi_commentary import get_match_commentary, save_commentary_to_file

    season = "Season 1"
    match_id = "6774"
    url = f"https://www.prokabaddi.com/matchcentre/{match_id}-scorecard"

    data = get_match_commentary(season, match_id, url)
    save_commentary_to_file(data, "output.json")
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re
import json

# ------------------ DRIVER SETUP ------------------

def _create_driver():
    """Create and configure a headless Chrome WebDriver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    return webdriver.Chrome(options=chrome_options)

# ------------------ TEAM-PROFILE PARSER ------------------

def _build_player_team_map(soup):
    """Return a dict mapping player names → team names."""
    player_team_map = {}
    for team_box in soup.select("div.team-box"):
        team_name_elem = team_box.select_one(".team-name, .teamTitle")
        if not team_name_elem:
            continue
        team_name = team_name_elem.get_text(strip=True)
        for player_elem in team_box.select(".player-list .player, .player-list .player-name, .player-name"):
            pname = player_elem.get_text(strip=True)
            if pname:
                player_team_map[pname.strip().lower()] = team_name
    return player_team_map

# ------------------ COMMENTARY PARSER ------------------

def _parse_event_from_commentary_section(block, player_team_map):
    """Extract structured event data from one commentary block."""
    half = minute = raider = event_type = team = tackled_by = None
    players_out = []
    do_or_die = all_out = False
    substitution = {}

    # Timer (Half + Minute)
    timer_div = block.select_one("div.body div.timer span.timer-text")
    if timer_div:
        txt = "".join(timer_div.stripped_strings)
        match = re.match(r"(\d+).+Half: ?(\d+)'", txt)
        if match:
            half = f"{match.group(1)} Half"
            minute = match.group(2)

    # Event Type
    points_header = block.select_one("div.match-commentary div.commentary-data div.points-history div.points-header")
    event_type = ""
    if points_header:
        label = points_header.select_one("span.label")
        title = points_header.select_one("span.title")
        label_text = label.get_text(strip=True) if label else ""
        title_text = title.get_text(strip=True) if title else ""
        event_type = label_text or title_text

        for sub in points_header.find_all("span", class_="sub-title"):
            if "do or die" in sub.text.lower():
                do_or_die = True
            if "all out" in sub.text.lower():
                all_out = True

    # Player Info
    data_blocks = block.select("div.match-commentary div.commentary-data")
    for cdata in data_blocks:
        for info in cdata.select("div.points-history div.points-information"):
            label = info.select_one("span.label")
            label_text = (
                label.get_text(strip=True).lower().replace(":", "").strip()
                if label else ""
            )

            player_elems = info.select("span.player-name")
            player_text = ", ".join([p.get_text(strip=True) for p in player_elems if p.get_text(strip=True)]) if player_elems else ""

            if "raider" in label_text:
                raider = player_text
            elif "players out" in label_text or "player out" in label_text:
                names = [x.strip() for x in player_text.split(",") if x.strip()]
                players_out.extend(names)
            elif "tackled by" in label_text:
                tackled_by = player_text
            elif label_text == "in":
                substitution["in"] = player_text
            elif label_text == "out":
                substitution["out"] = player_text

    # Team Mapping
    if raider and player_team_map:
        team = player_team_map.get(raider.strip().lower())

    # Points logic
    points = len(players_out) if event_type.lower() == "successful raid" else 0
    if event_type.lower() == "successful raid" and not players_out:
        points = 1

    # Description builder
    if "substitution" in event_type.lower() and substitution.get("in") and substitution.get("out"):
        desc = f"Substitution: In: {substitution['in']}; Out: {substitution['out']}."
    elif event_type.lower() == "successful raid" and raider:
        desc = f"{raider} executes a successful raid"
        desc += ", getting " + " and ".join(players_out) + " out." if players_out else "."
    elif event_type.lower() == "unsuccessful raid" and raider and tackled_by:
        desc = f"{raider} is tackled by {tackled_by} on an unsuccessful raid."
    elif event_type.lower() == "empty raid" and raider:
        desc = f"{raider} makes an empty raid."
    elif event_type in ["Timeout", "Toss"]:
        desc = event_type
    else:
        desc = block.get_text(" ", strip=True)

    return {
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
        "description": desc,
    }

# ------------------ MAIN SCRAPER ------------------

def get_match_commentary(season, match_id, match_url):
    """
    Scrape commentary data for a given match and return structured JSON.
    """
    driver = _create_driver()
    driver.get(match_url)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "playbyplay-section")))
    time.sleep(2)

    for _ in range(15):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    player_team_map = _build_player_team_map(soup)
    playbyplay_section = soup.select_one("div.playbyplay-section")

    events = []
    if playbyplay_section:
        for blk in playbyplay_section.select("div.commentary-section"):
            event_json = _parse_event_from_commentary_section(blk, player_team_map)
            events.append(event_json)

    return {
        "season": season,
        "match_id": match_id,
        "events": events
    }

# ------------------ SAVE UTILITY ------------------

def save_commentary_to_file(data, filename):
    """Save scraped match data (dict or list) into a JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved commentary data to {filename}")
