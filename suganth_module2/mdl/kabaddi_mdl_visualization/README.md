Kabaddi MDL Visualization - Final

Folders:
- server/: Flask backend. Put your JSON data files under server/public/data/
  Expected files:
    - season_1_matches.json ... season_12_matches.json
    - season_season_1_matches.json ... (optional)
    - prokabaddi_matches.json (optional; the script also tries /mnt/data/prokabaddi_matches.json)
- frontend/kabaddi_mdl_visualization/: React + Vite frontend

Run backend:
  cd server
  python -m venv venv
  source venv/bin/activate   # Windows: venv\Scripts\activate
  pip install -r requirements.txt
  python app.py

Run frontend:
  cd frontend/kabaddi_mdl_visualization
  npm install --legacy-peer-deps
  npm run dev

Open http://localhost:5173
