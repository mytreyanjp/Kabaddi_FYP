from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re
import json
#commentary enduka use panna file

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    return webdriver.Chrome(options=chrome_options)


def build_player_team_map(soup):
    """Extract team → player name mapping."""
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


def parse_event_from_commentary_section(block, player_team_map):
    half = None
    minute = None
    raider = None
    event_type = None
    team = None
    tackled_by = None
    players_out = []
    do_or_die = False
    all_out = False
    substitution = {}

    # 1. Timer extraction (Half + Time)
    timer_div = block.select_one("div.body div.timer span.timer-text")
    if timer_div:
        txt = "".join(timer_div.stripped_strings)
        match = re.match(r"(\d+).+Half: ?(\d+)'", txt)
        if match:
            half = f"{match.group(1)} Half"
            minute = match.group(2)

    # 2. Event type and sub-tags
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
            if "do or die" in sub.text.lower():
                do_or_die = True
            if "all out" in sub.text.lower():
                all_out = True

    # 3. Commentary data (usually raid info)
    data_blocks = block.select("div.match-commentary div.commentary-data")
    if data_blocks:
        cdata_raid = data_blocks[0]
        # Loop through all commentary-data blocks (raider + defenders + players-out)
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

                # Raider
                if "raider" in label_text:
                    raider = player_text

                # Players Out
                elif "players out" in label_text or "player out" in label_text:
                    names = [x.strip() for x in player_text.split(",") if x.strip()]
                    players_out.extend(names)

                # Tackled By
                elif "tackled by" in label_text:
                    tackled_by = player_text

                # Substitutions
                elif label_text == "in":
                    substitution["in"] = player_text
                elif label_text == "out":
                    substitution["out"] = player_text


        # Assign team via raider name mapping
        if raider and player_team_map:
            team = player_team_map.get(raider.strip().lower())

    # 4. Defender/tackle block (second commentary-data)
    if len(data_blocks) > 1:
        defenders_block = data_blocks[1]
        for info in defenders_block.select("div.points-history div.points-information"):
            label = info.select_one("span.label")
            player = info.select_one("span.player-name")
            label_text = label.get_text(strip=True).lower() if label else ""
            player_text = player.get_text(strip=True) if player else ""
            if label_text == "tackled by :" and player_text:
                tackled_by = player_text

    # 5. Points logic
    points = len(players_out) if event_type and event_type.lower() == "successful raid" else 0
    if event_type and event_type.lower() == "successful raid" and not players_out:
        points = 1

    # 6. Description builder
    if event_type and "substitution" in event_type.lower() and substitution.get("in") and substitution.get("out"):
        desc = f"Substitution: In: {substitution['in']}; Out: {substitution['out']}."
    elif event_type and event_type.lower() == "successful raid" and raider:
        desc = f"{raider} executes a successful raid"
        if players_out:
            desc += ", getting " + " and ".join(players_out) + " out."
        else:
            desc += "."
    elif event_type and event_type.lower() == "unsuccessful raid" and raider and tackled_by:
        desc = f"{raider} is tackled by {tackled_by} on an unsuccessful raid."
    elif event_type and event_type.lower() == "empty raid" and raider:
        desc = f"{raider} makes an empty raid."
    elif event_type in ["Timeout", "Toss"]:
        desc = event_type
    else:
        desc = block.get_text(" ", strip=True)

    # 7. Build JSON output
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
        "description": desc,
    }
    return event_json


def kabaddi_commentary_from_url(match_url):
    driver = create_driver()
    driver.get(match_url)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "playbyplay-section")))
    time.sleep(2)
    for _ in range(15):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    # Build team-player map
    player_team_map = build_player_team_map(soup)
    playbyplay_section = soup.select_one("div.playbyplay-section")

    events = []
    if playbyplay_section:
        commentary_blocks = playbyplay_section.select("div.commentary-section")
        print("Found", len(commentary_blocks), "commentary-section divs")
        for i, blk in enumerate(commentary_blocks):
            event_json = parse_event_from_commentary_section(blk, player_team_map)

            # Skip completely empty sections
            if not event_json["event_type"] and not event_json["players_out"]:
                continue

            # 🔁 Merge: If "Successful Raid" has no players_out,
            # and the next block has only players_out (no event_type)
            if (
                event_json["event_type"]
                and "successful raid" in event_json["event_type"].lower()
                and not event_json["players_out"]
                and i + 1 < len(commentary_blocks)
            ):
                next_json = parse_event_from_commentary_section(commentary_blocks[i + 1], player_team_map)
                if not next_json["event_type"] and next_json["players_out"]:
                    event_json["players_out"] = next_json["players_out"]
                    event_json["points"] = len(next_json["players_out"]) or 1
                    event_json["description"] = (
                        f"{event_json['raider']} executes a successful raid, getting "
                        + " and ".join(event_json["players_out"]) 
                        + " out."
                    )

            # ✅ Append after possible merge
            if event_json["event_type"]:
                events.append(event_json)
    return events


if __name__ == "__main__":
    url = "https://www.prokabaddi.com/matchcentre/6774-scorecard"
    results = kabaddi_commentary_from_url(url)
    with open("kabaddi__commentary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"✅ Extracted {len(results)} events and saved as kabaddi__commentary.json")
