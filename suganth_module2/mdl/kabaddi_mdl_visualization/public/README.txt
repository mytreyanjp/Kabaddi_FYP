Place your JSON files into this folder before running the app.

Expected files (examples):
- season_index.json              (optional) index file summarizing matches per season
- season_1_matches.json ... season_12_matches.json   (per-match player stats)
- prokabaddi_commentary_season5plus.json             (commentary events)
- teams_list.json               (optional small file listing team names)

If you don't have season_index.json, the app will attempt to read season_1..12_matches.json to find matches.

Then run:
  npm install
  npm run dev
