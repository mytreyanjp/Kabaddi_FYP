import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
#each match oda player and team details scrape panna
# HARDCODE all Season 1 links here.
season1_links = [
    f"https://www.prokabaddi.com/matchcentre/{i}-scorecard"
    for i in range(1, 61)
]

results = []

for match_url in season1_links:
    driver = webdriver.Chrome()
    driver.get(match_url)
    time.sleep(4)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # --- Your scraping logic as before ---
    title = soup.select_one("div.head-wrap h1")
    if title:
        match_text = title.get_text(strip=True)
        match_text = match_text.replace(", Pro Kabaddi League", "")
        teams = match_text.split(" vs ")
        teamA = teams[0].strip() if len(teams) > 0 else "TeamA"
        teamB = teams[1].strip() if len(teams) > 1 else "TeamB"
    else:
        teamA = "TeamA"
        teamB = "TeamB"

    team_a_score_tag = soup.select_one("div.team.team-a p.score")
    team_b_score_tag = soup.select_one("div.team.team-b p.score")
    team_a_score = team_a_score_tag.get_text(strip=True) if team_a_score_tag else ""
    team_b_score = team_b_score_tag.get_text(strip=True) if team_b_score_tag else ""

    def get_players_from_scorecard_list(list_div, player_role, team_name):
        players = []
        for item in list_div.select("div.scorecard-item"):
            pdetail = item.select_one("div.player-detail")
            if not pdetail:
                continue
            first = pdetail.select_one(".first-name")
            last = pdetail.select_one(".last-name")
            name = f"{first.get_text(strip=True) if first else ''} {last.get_text(strip=True) if last else ''}".strip()
            category = pdetail.select_one(".category")
            category = category.get_text(strip=True) if category else ""
            points = pdetail.select_one(".points-count")
            points = points.get_text(strip=True) if points else "0"
            details = {}
            more = item.select_one("div.more-player-detail")
            if more:
                for pt in more.select("div.points-item"):
                    label = pt.select_one(".points-label")
                    value = pt.select_one(".points-value")
                    if label and value:
                        details[label.get_text(strip=True)] = value.get_text(strip=True)
                for raid_type in ["raid-points-history", "Tackle-points-history"]:
                    history = more.select_one(f".points-history.{raid_type}")
                    if history:
                        history_title = history.select_one('.title')
                        history_count = history.select_one('.count')
                        if history_title and history_count:
                            details[history_title.get_text(strip=True)] = history_count.get_text(strip=True)
                        for graph in history.select('.graph-item'):
                            glabel = graph.select_one('.graph-label')
                            gval = graph.select_one('.graph-value')
                            if glabel and gval:
                                details[glabel.get_text(strip=True)] = gval.get_text(strip=True)
            player_data = {
                "team_name": team_name,
                "name": name,
                "player_role": player_role,
                "category": category,
                "points": points,
                **details
            }
            players.append(player_data)
        return players

    players = []
    for section_cls, player_role in [
            ("scorecard-starter-section", "Starters"),
            ("scorecard-substitute-section", "Substitutes")]:
        for team_idx, team_cls in enumerate(("scorecard-list-a", "scorecard-list-b")):
            section = soup.find("div", class_=f"scorecard-section {section_cls}")
            if section is not None:
                team_div = section.find("div", class_=f"scorecard-list {team_cls}")
                if team_div:
                    team_name = teamA if team_idx == 0 else teamB
                    players += get_players_from_scorecard_list(team_div, player_role, team_name)

    match_name = ''
    for tag in soup.find_all("h4", class_="title"):
        text = tag.get_text(strip=True)
        if text not in ("Starters", "Substitutes"):
            match_name = text
            break
    venue_tag = soup.select_one('h4.matchinfo')
    venue = venue_tag.text.strip() if venue_tag else ""

    # Click the "Team Stats" tab
    try:
        team_stats_tab = driver.find_element(By.ID, "tab3")
        team_stats_tab.click()
        time.sleep(2)
    except Exception:
        pass

    team_stats = {}
    stats_soup = BeautifulSoup(driver.page_source, "html.parser")
    first_half_stats = {}
    pb_listing = stats_soup.select_one("div.progressbar-listing")
    if pb_listing:
        for pb_item in pb_listing.find_all("div", class_="progressbar-item"):
            label_tag = pb_item.select_one("div.label-wrap p.label")
            score_a_tag = pb_item.select_one("p.team-score.team-score-a")
            score_b_tag = pb_item.select_one("p.team-score.team-score-b")
            if label_tag:
                stat_name = label_tag.get_text(strip=True)
                first_half_stats[stat_name] = {
                    teamA: score_a_tag.get_text(strip=True) if score_a_tag else "",
                    teamB: score_b_tag.get_text(strip=True) if score_b_tag else ""
                }
    team_stats["First Half"] = first_half_stats

    # SECOND HALF - click the sub-tab
    try:
        second_half_tab = driver.find_element(By.ID, "second-half")
        second_half_tab.click()
        time.sleep(2)
    except Exception:
        pass

    # Re-parse after clicking second half
    stats_soup = BeautifulSoup(driver.page_source, "html.parser")
    second_half_stats = {}
    pb_listing = stats_soup.select_one("div.progressbar-listing")
    if pb_listing:
        for pb_item in pb_listing.find_all("div", class_="progressbar-item"):
            label_tag = pb_item.select_one("div.label-wrap p.label")
            score_a_tag = pb_item.select_one("p.team-score.team-score-a")
            score_b_tag = pb_item.select_one("p.team-score.team-score-b")
            if label_tag:
                stat_name = label_tag.get_text(strip=True)
                second_half_stats[stat_name] = {
                    teamA: score_a_tag.get_text(strip=True) if score_a_tag else "",
                    teamB: score_b_tag.get_text(strip=True) if score_b_tag else ""
                }
    team_stats["Second Half"] = second_half_stats

    driver.quit()

    result = {
        "match_url": match_url,
        "match_name": match_name,
        "venue": venue,
        "teams": [
            {"team_name": teamA, "score": team_a_score, "players": [p for p in players if p["team_name"] == teamA]},
            {"team_name": teamB, "score": team_b_score, "players": [p for p in players if p["team_name"] == teamB]}
        ],
        "team_stats": team_stats
    }
    results.append(result)

# Save all matches as one JSON file
with open("season1_matches.json", "w", encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

# To display results print at end if needed:
print(json.dumps(results, indent=2))
