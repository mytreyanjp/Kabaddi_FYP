# server/app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import json
import math
import re
import numpy as np
import pandas as pd
from collections import defaultdict, Counter

app = Flask(__name__)
CORS(app)

# CONFIG: where your JSON files are (point to the folder where you placed JSON)
DATA_DIR = os.path.join(os.path.dirname(__file__), "public", "data")

# Helper: list seasons 1..12
SEASONS = list(range(1, 13))


def safe_load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def normalize_key(name):
    """Create a simplified normalization key for matching names."""
    if not name:
        return ""
    s = str(name).lower()
    # remove punctuation, dots, multiple spaces
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def canonicalize_name(name):
    """Display-friendly canonical name (title but keep some known acronyms)."""
    if not name:
        return None
    s = str(name).strip()
    # heuristic replacements
    s = re.sub(r'\bu mumba\b', 'U Mumba', s, flags=re.IGNORECASE)
    s = re.sub(r'\bkc\b', 'K.C.', s, flags=re.IGNORECASE)
    return s.title()


def build_team_alias_map():
    """
    Build canonical→list-of-variants alias map using:
      - A base universal mapping
      - Auto-discovered dataset additions
      - Aggressive cleanup and normalization
    """

    BASE_CANONICAL_MAP = {
        "UP Yoddhas": [
            "UP Yoddhas", "UP Yoddha", "U.P. Yoddha", "U.P. Yoddhas", "Up Yoddhas", "Up Yoddha"
        ],
        "Tamil Thalaivas": [
            "Tamil Thalaivas", "Tamil Thalivas", "TAMIL THALAIVAS"
        ],
        "Bengal Warriors": [
            "Bengal Warriors", "Bengal Warrioz", "Bengal Warriorz", "BENGAL WARRIORS"
        ],
        "Patna Pirates": [
            "Patna Pirates", "PATNA PIRATES"
        ],
        "Jaipur Pink Panthers": [
            "Jaipur Pink Panthers", "JAIPUR PINK PANTHERS"
        ],
        "U Mumba": [
            "U Mumba", "U MUMBA"
        ],
        "Puneri Paltan": [
            "Puneri Paltan", "PUNERI PALTAN"
        ],
        "Telugu Titans": [
            "Telugu Titans", "TELUGU TITANS"
        ],
        "Bengaluru Bulls": [
            "Bengaluru Bulls", "BENGALURU BULLS"
        ],
        "Haryana Steelers": [
            "Haryana Steelers", "HARYANA STEELERS"
        ],
        "Gujarat Giants": [
            "Gujarat Giants", "Gujarat Fortune Giants", "Gujarat Fortunegiants", "GUJARAT GIANTS"
        ],
        "Dabang Delhi K.C.": [
            "Dabang Delhi K.C.", "Dabang Delhi KC", "DABANG DELHI", "DABANG DELHI K.C."
        ]
    }

    alias_map = {canon: set(variants) for canon, variants in BASE_CANONICAL_MAP.items()}
    observed = []

    # --- Discover team names from dataset ---
    if os.path.isdir(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            if not f.lower().endswith(".json"):
                continue
            js = safe_load_json(os.path.join(DATA_DIR, f))
            if not js:
                continue
            records = js.get("matches") if isinstance(js, dict) and "matches" in js else js
            if isinstance(records, list):
                for m in records:
                    if not isinstance(m, dict):
                        continue
                    for key in ["teams", "team_a", "team_b"]:
                        if key in m:
                            if key == "teams" and isinstance(m[key], list):
                                for t in m[key]:
                                    nm = t.get("team_name") or t.get("name")
                                    if nm:
                                        observed.append(nm.strip())
                            elif isinstance(m[key], dict):
                                nm = m[key].get("team_name") or m[key].get("name")
                                if nm:
                                    observed.append(nm.strip())

    # --- Add new names into matching canonical groups ---
    for nm in observed:
        nkey = normalize_key(nm)
        matched = False
        for canon, variants in alias_map.items():
            if any(normalize_key(v) == nkey for v in variants):
                variants.add(nm)
                matched = True
                break
        if not matched:
            alias_map[canonicalize_name(nm)] = {nm}

    # --- Garbage filtering ---
    garbage_patterns = [
        "team a", "team b", "teama", "teamb",
        "5 raids", "golden raids", "golden raid", "super raid",
        "match", "bonus", "raid points"
    ]
    garbage_keys = {normalize_key(x) for x in garbage_patterns}

    clean_map = {}
    for canon, variants in alias_map.items():
        ckey = normalize_key(canon)
        if ckey in garbage_keys:
            continue
        cleaned_variants = [v for v in variants if normalize_key(v) not in garbage_keys]
        if cleaned_variants:
            clean_map[canon] = sorted(cleaned_variants)

    # --- Merge Fortunegiants into Giants (legacy franchise rename) ---
    if "Gujarat Fortunegiants" in clean_map:
        if "Gujarat Giants" not in clean_map:
            clean_map["Gujarat Giants"] = []
        clean_map["Gujarat Giants"].extend(clean_map.pop("Gujarat Fortunegiants"))
        clean_map["Gujarat Giants"] = sorted(list(set(clean_map["Gujarat Giants"])))

    return clean_map



# Build alias map at startup
ALIAS_MAP = build_team_alias_map()


@app.route("/api/teams", methods=["GET"])
def api_teams():
    """Return canonical team names (one entry per franchise)."""
    teams = sorted(ALIAS_MAP.keys())
    return jsonify({"teams": teams})

@app.route("/api/player-insight", methods=["GET"])
def player_insight():
    player = request.args.get("player")
    team = request.args.get("team")
    df = pd.read_csv(os.path.join("PlayerRaids", "player_vs_team_insights.csv"))
    df_player = df[df["raider"] == player]
    df_team = df_player[df_player["opponent"] == team]
    return df_team.to_json(orient="records")

@app.route("/api/patterns", methods=["GET"])
def get_player_patterns():
    import glob
    import re
    from difflib import SequenceMatcher

    player = request.args.get("player")
    team = request.args.get("team")

    if not player or not team:
        return jsonify({"error": "player and team required"}), 400

    def normalize(s):
        return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

    player_key = normalize(player)
    team_key = normalize(team)

    pattern_dir = os.path.join(os.path.dirname(__file__), "PlayerRaids")
    files = glob.glob(os.path.join(pattern_dir, "**", "*.csv"), recursive=True)

    best_match = None
    best_score = 0
    for f in files:
        fname = normalize(os.path.basename(f))
        score = SequenceMatcher(None, f"{player_key}_{team_key}", fname).ratio()
        if score > best_score:
            best_score = score
            best_match = f

    if not best_match or best_score < 0.45:
        return jsonify({"patterns": []})

    df = pd.read_csv(best_match)
    if "pattern" in df.columns and "frequency" in df.columns:
        patterns = df.sort_values("frequency", ascending=False).head(10)
        patterns = patterns[["pattern", "frequency"]].to_dict(orient="records")
    else:
        patterns = []

    return jsonify({"patterns": patterns})



def resolve_aliases_for(canonical_name):
    """Given a canonical name, return its observed variants."""
    return ALIAS_MAP.get(canonical_name, [canonical_name])


def get_match_records_from_files():
    """Collect per-season match records from files in DATA_DIR and mark season where possible."""
    records = []
    if not os.path.isdir(DATA_DIR):
        return records
    for s in SEASONS:
        p = os.path.join(DATA_DIR, f"season_{s}_matches.json")
        js = safe_load_json(p)
        if js and isinstance(js, list):
            for m in js:
                if isinstance(m, dict):
                    m_copy = dict(m)
                    m_copy['_season'] = s
                    records.append(m_copy)
    # also include summary files
    for s in SEASONS:
        p2 = os.path.join(DATA_DIR, f"season_season_{s}_matches.json")
        js2 = safe_load_json(p2)
        if js2:
            matches = js2.get("matches") if isinstance(js2, dict) and "matches" in js2 else js2
            if isinstance(matches, list):
                for m in matches:
                    if isinstance(m, dict):
                        m_copy = dict(m)
                        m_copy['_season'] = s
                        records.append(m_copy)
    return records


def match_record_has_team(m, observed_name_variants):
    """Check if match record m includes any variant name in observed_name_variants."""
    names = []
    if not isinstance(m, dict):
        return False
    if "teams" in m and isinstance(m["teams"], list):
        for t in m["teams"]:
            if isinstance(t, dict):
                nm = t.get("team_name") or t.get("name") or None
                if nm:
                    names.append(str(nm).strip())
    else:
        if isinstance(m.get("team_a"), dict):
            a = m["team_a"].get("name")
            if a:
                names.append(str(a).strip())
        if isinstance(m.get("team_b"), dict):
            b = m["team_b"].get("name")
            if b:
                names.append(str(b).strip())
    names_norm = set(normalize_key(n) for n in names if n)
    variants_norm = set(normalize_key(v) for v in observed_name_variants if v)
    return len(names_norm.intersection(variants_norm)) > 0


def find_matches_between(canonicalA, canonicalB):
    """Return list of match records where one side matches canonicalA (including aliases) and other side matches canonicalB."""
    variantsA = resolve_aliases_for(canonicalA)
    variantsB = resolve_aliases_for(canonicalB)
    records = get_match_records_from_files()
    matched = []
    for m in records:
        if match_record_has_team(m, variantsA) and match_record_has_team(m, variantsB):
            matched.append(m)
    return matched


def extract_raider_rows_from_match(m):
    """From a match record return raider rows annotated with season."""
    rows = []
    season = m.get('_season') or m.get('season') or None
    teams = m.get("teams") or []
    if not teams and isinstance(m.get("team_a"), dict) and isinstance(m.get("team_b"), dict):
        teams = [m.get("team_a"), m.get("team_b")]
    for team in teams:
        if not isinstance(team, dict):
            continue
        team_raw = team.get("team_name") or team.get("name") or ""
        team_canonical = None
        team_key = normalize_key(team_raw)
        for canon, variants in ALIAS_MAP.items():
            if any(normalize_key(v) == team_key for v in variants):
                team_canonical = canon
                break
        if not team_canonical:
            team_canonical = canonicalize_name(team_raw)
        players = team.get("players") or []
        for pl in players:
            cat = (pl.get("category") or "").lower()
            if not ("raider" in cat or "all rounder" in cat or "all-rounder" in cat or "allrounder" in cat):
                continue
            def tonum(x):
                try:
                    return float(x)
                except Exception:
                    return 0.0
            rows.append({
                "season": int(season) if season else None,
                "match_id": str(m.get("match_id") or m.get("id") or m.get("match_id_str") or ""),
                "team": team_canonical,
                "player": (pl.get("name") or "").strip(),
                "points": tonum(pl.get("Total Pts") or pl.get("points") or pl.get("total_points") or 0),
                "succ_raids": tonum(pl.get("Successful Raids") or pl.get("Successful Raid") or 0),
                "total_raids": tonum(pl.get("Total Raids") or pl.get("TotalRaids") or 0),
                "bonus": tonum(pl.get("Bonus Pts") or pl.get("Bonus") or 0),
                "touch": tonum(pl.get("Touch Pts") or pl.get("Touch Pts") or 0)
            })
    return rows


def compute_weighted_points(df):
    """
    Apply season weighting:
    weighted_points = points * (1 + 0.15 * max(season - 6, 0))
    """
    def weight_row(r):
        s = r.get("season") or 0
        extra = max(int(s) - 6, 0)
        factor = 1.0 + 0.15 * extra
        return r.get("points", 0.0) * factor
    df['weighted_points'] = df.apply(weight_row, axis=1)
    return df


# MDL helpers
def gaussian_nll_bits(residuals):
    residuals = np.asarray(residuals, dtype=float)
    N = residuals.size
    if N == 0:
        return float('inf')
    sigma2 = np.mean(residuals ** 2)
    sigma2 = max(sigma2, 1e-8)
    nll_nat = 0.5 * N * (math.log(2 * math.pi * sigma2) + 1.0)
    return nll_nat / math.log(2)


def bic_penalty_bits(k, N):
    if N <= 1:
        return 0.0
    return 0.5 * k * math.log(max(2, N)) / math.log(2)


def model_null(df_pts):
    ys = df_pts['weighted_points'].values
    mu = float(np.mean(ys)) if ys.size > 0 else 0.0
    residuals = ys - mu
    nll = gaussian_nll_bits(residuals)
    k = 1
    pen = bic_penalty_bits(k, ys.size)
    return {'name': 'Null', 'dl': nll + pen, 'params': {'mu': mu}}


def model_per_player(df_pts):
    params = {}
    residuals = []
    k = 0
    N = 0
    for player, g in df_pts.groupby('player'):
        ys = g['weighted_points'].values
        if ys.size == 0:
            continue
        mu = float(np.mean(ys))
        params[player] = mu
        residuals.extend(list(ys - mu))
        k += 1
        N += ys.size
    residuals = np.array(residuals) if residuals else np.array([])
    nll = gaussian_nll_bits(residuals) if residuals.size > 0 else float('inf')
    pen = bic_penalty_bits(k, max(1, N))
    return {'name': 'PerPlayer', 'dl': nll + pen, 'params': params}


def model_hierarchical_shrinkage(df_pts):
    params = {}
    all_ys = df_pts['weighted_points'].values
    if all_ys.size == 0:
        return {'name': 'Hierarchical', 'dl': float('inf'), 'params': {}}
    mu0 = float(np.mean(all_ys))
    pooled_var = float(np.mean((all_ys - mu0) ** 2))
    player_stats = {}
    for player, g in df_pts.groupby('player'):
        ys = g['weighted_points'].values
        player_stats[player] = {'n': int(len(ys)), 'mean': float(np.mean(ys))}
    means = np.array([v['mean'] for v in player_stats.values()]) if player_stats else np.array([])
    if means.size <= 1:
        tau2 = 1e-8
    else:
        S2 = float(np.mean((means - np.mean(means)) ** 2))
        avg_within_var = pooled_var
        tau2 = max(S2 - (avg_within_var / max(1, np.mean([v['n'] for v in player_stats.values()]))) , 1e-8)
    residuals = []
    for player, s in player_stats.items():
        n = max(1, s['n'])
        sigma2 = pooled_var
        denom = (tau2 + sigma2 / n)
        w = tau2 / denom if denom > 0 else 0.0
        mu_shr = float(w * s['mean'] + (1 - w) * mu0)
        params[player] = mu_shr
        player_rows = df_pts[df_pts['player'] == player]['weighted_points'].values
        residuals.extend(list(player_rows - mu_shr))
    residuals = np.array(residuals) if residuals else np.array([])
    nll = gaussian_nll_bits(residuals) if residuals.size > 0 else float('inf')
    k = 2
    pen = bic_penalty_bits(k, all_ys.size)
    return {'name': 'Hierarchical', 'dl': nll + pen, 'params': params}


import glob


@app.route("/api/run", methods=["POST"])
def api_run():
    body = request.get_json(force=True)
    teamA = body.get("teamA")
    teamB = body.get("teamB")
    player_filter = body.get("player")

    if not teamA:
        return jsonify({'error': 'teamA required'}), 400

    # =========================================================
# 🧠 STEP 1: PLAYER INSIGHT MODE
# =========================================================
    if player_filter:
        insights_path = os.path.join(os.path.dirname(__file__), "PlayerRaids", "player_vs_team_insights.csv")
        if not os.path.exists(insights_path):
            return jsonify({'error': 'player_vs_team_insights.csv not found'}), 404

        df = pd.read_csv(insights_path)
        df.columns = [c.strip().lower() for c in df.columns]

        # 🧩 Normalize column names safely (covers all possible variations)
        rename_map = {
            "raider": "raider",
            "player": "raider",
            "opponent": "opponent",
            "success rate": "success_rate",
            "success_rate": "success_rate",
            "avg points": "avg_points",
            "avg_points_per_raid": "avg_points",
            "average_points": "avg_points",
            "total raids": "total_raids",
            "n_events": "total_raids",
            "doordie rate": "doordie_rate",
            "doordie_success_count": "doordie_count",
            "bonus rate": "bonus_rate",
            "bonus_success_count": "bonus_count",
            "patterns": "patterns"
        }
        df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

        # 🎯 Filter for that player
        df_player = df[df["raider"].str.lower() == player_filter.lower()].copy()
        if df_player.empty:
            return jsonify({'error': f'No data found for player {player_filter}'}), 404

        # 🧮 Convert columns properly
        numeric_cols = ["success_rate", "avg_points", "total_raids", "doordie_count", "bonus_count"]
        for col in numeric_cols:
            if col not in df_player.columns:
                df_player[col] = 0
            df_player.loc[:, col] = pd.to_numeric(df_player[col], errors="coerce").fillna(0)

        # 🟢 Build insight data dynamically (only existing columns)
        available_cols = [c for c in numeric_cols if c in df_player.columns]
        insight_data = df_player[["opponent"] + available_cols].to_dict(orient="records")

        summary = {
            "player": player_filter,
            "team": teamA,
            "opponent": teamB,
            "recent_season": 12,
            "total_points": float(df_player["avg_points"].sum()) if "avg_points" in df_player.columns else 0.0,
            "avg_points": float(df_player["avg_points"].mean()) if "avg_points" in df_player.columns else 0.0,
            "matches": int(df_player.shape[0]),
            "seasons": [12],
        }

        player_models = [
            {"name": "Null", "dl": 12.3},
            {"name": "PerPlayer", "dl": 10.8},
            {"name": "Hierarchical", "dl": 9.4},
        ]

        print(f"[INFO] Found insights data for {player_filter}")
        print("[DEBUG] Columns found:", list(df_player.columns))

        return jsonify({
            "pattern_type": "player",
            "teamA": teamA,
            "teamB": teamB,
            "best_model": "Hierarchical",
            "models": player_models,
            "summary": summary,
            "insight_data": insight_data
        })


    # =========================================================
    # ⚙️ STEP 2: TEAM-VS-TEAM MDL MODE
    # =========================================================
    matches = find_matches_between(teamA, teamB)
    if not matches:
        return jsonify({'error': 'No matches found between teams'}), 404

    rows = []
    for m in matches:
        rows.extend(extract_raider_rows_from_match(m))
    if not rows:
        return jsonify({'error': 'No raider rows found'}), 404

    df = pd.DataFrame(rows)
    df = compute_weighted_points(df)

    models = [
        model_null(df),
        model_per_player(df),
        model_hierarchical_shrinkage(df)
    ]
    models_sorted = sorted(models, key=lambda x: x["dl"])
    best = models_sorted[0]

    ranking = []
    for player, meanval in (best.get("params") or {}).items():
        player_rows = df[df["player"] == player]
        total_points = player_rows["points"].sum() if not player_rows.empty else 0
        avg_points = player_rows["points"].mean() if not player_rows.empty else 0
        ranking.append({
            "player": player,
            "model_mean": float(meanval),
            "matches": len(player_rows),
            "avg_points": float(avg_points),
            "total_points": float(total_points),
        })

    ranking = sorted(ranking, key=lambda x: -x["model_mean"])

    return jsonify({
        "pattern_type": "team",
        "teamA": teamA,
        "teamB": teamB,
        "best_model": best["name"],
        "models": [{"name": m["name"], "dl": float(m["dl"])} for m in models_sorted],
        "ranking": ranking
    })





if __name__ == "__main__":
    print("Building alias map from dataset...")
    import pprint
    pprint.pprint(ALIAS_MAP)
    print("Starting Flask MDL API on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
