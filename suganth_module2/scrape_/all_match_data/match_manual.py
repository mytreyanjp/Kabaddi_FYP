from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import json
import re
#12 seasons ah manual ah select panni match data ah scrape pannathu
chrome_options = Options()
chrome_options.add_argument('--start-maximized')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')

driver = webdriver.Chrome(options=chrome_options)

try:
    print("🌐 Loading Pro Kabaddi schedule page...")
    driver.get("https://www.prokabaddi.com/schedule-fixtures-results")
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".filter-wrap")))
    time.sleep(3)

    # List of seasons to scrape manually
    seasons_to_scrape = [f"Season {i}" for i in range(1, 13)]
    all_seasons_data = []

    for target_season in seasons_to_scrape:
        print(f"\n{'='*70}\n🎯 Preparing to scrape {target_season}\n{'='*70}")

        # --- Open dropdown for manual selection ---
        dropdown_button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, ".filter-wrap .waf-select-box:nth-child(1) .selected-title")
        ))
        driver.execute_script("arguments[0].click();", dropdown_button)
        print(f"\n🔽 Dropdown opened — please manually select **{target_season}** in the browser.")
        input("⏸ Press ENTER after you've selected it...")

        # --- Verify that season changed ---
        print("⏳ Waiting for page to update...")
        try:
            wait.until(EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, ".filter-wrap .waf-select-box:nth-child(1) .selected-title .title"),
                target_season
            ))
        except:
            print("⚠️ Timeout waiting for season text, checking manually...")

        season_title = driver.find_element(
            By.CSS_SELECTOR, ".filter-wrap .waf-select-box:nth-child(1) .selected-title .title"
        ).text.strip()
        print(f"✅ Current selected season: {season_title}")

        # --- Click "Recent" tab ---
        print("\nClicking 'Recent' tab...")
        try:
            recent_tab = driver.find_element(By.XPATH, "//div[contains(text(), 'Recent')]")
            driver.execute_script("arguments[0].click();", recent_tab)
            time.sleep(3)
        except:
            print("⚠️ Could not click Recent tab, continuing anyway...")

        # --- Scroll to load all matches ---
        print("⬇️ Scrolling to load all matches...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        for i in range(15):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            print(f"Scroll {i + 1}/15")

        print("✅ Finished scrolling, extracting matches...")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        matches_list = []

        # --- Extract matches ---
        match_links = soup.find_all("a", href=re.compile(r"/matchcentre/\d+-scorecard"))
        print(f"Found {len(match_links)} matches for {target_season}")

        for link in match_links:
            try:
                match_url = "https://www.prokabaddi.com" + link["href"]
                match_id = re.search(r"/matchcentre/(\d+)-scorecard", link["href"]).group(1)
                parts = [p.strip() for p in link.get_text("|", strip=True).split("|") if p.strip()]
                teams = [p for p in parts if len(p) > 3 and not p.isdigit() and p not in ["FT", "HT", "LIVE"]]
                scores = [p for p in parts if p.isdigit()]
                status = next((p for p in parts if p in ["FT", "HT", "LIVE"]), "FT")

                if len(teams) < 2:
                    continue

                team_a, team_b = teams[0], teams[1]
                score_a, score_b = (scores + ["", ""])[:2]

                matches_list.append({
                    "match_id": match_id,
                    "match_url": match_url,
                    "team_a": {"name": team_a, "score": score_a},
                    "team_b": {"name": team_b, "score": score_b},
                    "status": status
                })
                print(f"  ➤ {team_a} vs {team_b}")
            except Exception as e:
                print(f"⚠️ Error parsing match: {e}")

        # --- Save per-season data ---
        season_data = {
            "season": target_season,
            "total_matches": len(matches_list),
            "matches": matches_list
        }
        all_seasons_data.append(season_data)

        # Save after each season
        with open(f"season_{target_season.replace(' ', '_').lower()}_matches.json", "w", encoding="utf-8") as f:
            json.dump(season_data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Saved {len(matches_list)} matches for {target_season}")
        time.sleep(2)

    # --- Save all seasons together ---
    with open("prokabaddi_matches.json", "w", encoding="utf-8") as f:
        json.dump(all_seasons_data, f, indent=2, ensure_ascii=False)

    print("\n🏁 All seasons scraped and saved successfully!")

finally:
    print("\nClosing browser...")
    driver.quit()
    print("Done!")
