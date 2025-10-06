import pandas as pd
import itertools
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def create_explanatory_synergy_matrix(
    team_players, player_stats_df, match_results_df, events_df,
    weights={'matches': 0.4, 'individual_success': 0.3, 'style': 0.3},
    baseline_position_synergy=None
):
    print("="*60)
    print("=== STARTING EXPLANATORY SYNERGY CALCULATION ===")
    print("="*60)

    # --- 1. Default Position-Based Synergy Map ---
    if baseline_position_synergy is None:
        baseline_position_synergy = {
            ('raider', 'raider'): 0.3,
            ('raider', 'defender'): 0.7,
            ('raider', 'allrounder'): 0.6,
            ('defender', 'defender'): 0.4,
            ('defender', 'allrounder'): 0.6,
            ('allrounder', 'allrounder'): 0.5,
        }

    # --- 2. Data Cleaning ---
    print("\nStep 1: Cleaning key columns...")
    player_stats_df['Player Name'] = player_stats_df['Player Name'].str.strip()
    player_stats_df['Team'] = player_stats_df['Team'].str.strip()
    events_df['player_name'] = events_df['player_name'].str.strip()
    match_results_df['home_team_name'] = match_results_df['home_team_name'].str.strip()
    print("-> Data cleaning complete.")

    # --- 3. Precompute Player History and Positions ---
    print("\nStep 2: Preprocessing player history and positions...")
    player_history = {
        p: set(map(tuple, player_stats_df[player_stats_df['Player Name'] == p][['Season', 'Team']].values))
        for p in team_players
    }

    player_positions = {}
    for p in team_players:
        row = player_stats_df[player_stats_df['Player Name'] == p]
        if not row.empty:
            if 'tag' in row.columns:
                player_positions[p] = row['tag'].iloc[0].lower()
            else:
                player_positions[p] = 'unknown'
        else:
            player_positions[p] = 'unknown'
    print("-> Player history and positions preprocessed.")

    # --- 4. Compute individual success rates ---
    print("\nStep 3: Computing individual success rates...")
    success_events = ['Raid Successful', 'Tackle Successful', 'Super Raid', 'Super Tackle']
    player_success_rate = {}
    for p in team_players:
        player_data = events_df[events_df['player_name'] == p]
        for season in player_data['season'].unique():
            season_data = player_data[player_data['season'] == season]
            total = len(season_data)
            success = season_data['event_type'].isin(success_events).sum()
            rate = success / total if total > 0 else 0
            player_success_rate[(p, season)] = rate
    print("-> Success rates computed.")

    # --- 5. Compute style vectors ---
    print("\nStep 4: Precomputing player style vectors...")
    event_types = ['Assist','Bonus Point','Raid Successful','Raid Unsuccessful',
                   'Super Raid','Super Tackle','Tackle Successful','Tackle Unsuccessful']

    player_style_vectors = {}
    for p in team_players:
        player_events = events_df[events_df['player_name'] == p]
        vector = []
        total_events = len(player_events)
        for et in event_types:
            count = (player_events['event_type'] == et).sum()
            vector.append(count / total_events if total_events > 0 else 0)
        player_style_vectors[p] = np.array(vector)
    print("-> Player style vectors computed.")

    # --- 6. Initialize synergy matrix ---
    print("\nStep 5: Initializing synergy matrix...")
    synergy_matrix = pd.DataFrame(0.0, index=team_players, columns=team_players)

    # --- 7. Compute pairwise synergy with explanatory prints ---
    print("\nStep 6: Computing pairwise synergy with explanations...")
    for player_a, player_b in itertools.combinations(team_players, 2):
        print("\n" + "-"*60)
        print(f"Analyzing Pair: {player_a} & {player_b}")
        print("-"*60)

        # Step 6a: Check common history
        common_history = player_history[player_a].intersection(player_history[player_b])
        if common_history:
            print(f"Players have shared seasons/teams: {common_history}")
        else:
            print("Players have no shared seasons/teams.")

        # Step 6b: Common matches
        total_matches_together = 0
        if common_history:
            common_matches_df = pd.DataFrame()
            for season, team in common_history:
                team_matches = match_results_df[
                    (match_results_df['home_team_name'] == team) & 
                    (match_results_df['season'] == season)
                ]
                common_matches_df = pd.concat([common_matches_df, team_matches])
            total_matches_together = len(common_matches_df)

        if total_matches_together > 0:
            print(f"Players played {total_matches_together} matches together → contributes to match-based synergy.")
        else:
            print("No common matches found → match-based synergy = 0.")

        match_score = min(total_matches_together / 10.0, 1.0) if total_matches_together > 0 else 0

        # Step 6c: Individual success score
        success_scores = []
        for season, _ in common_history:
            score_a = player_success_rate.get((player_a, season), 0)
            score_b = player_success_rate.get((player_b, season), 0)
            success_scores.append((score_a + score_b) / 2)
        success_score = sum(success_scores)/len(success_scores) if success_scores else 0
        if success_score > 0:
            print(f"Average success score based on shared seasons: {success_score:.2f}")
        else:
            print("No shared season success info → individual success score = 0.")

        # Step 6d: Style similarity
        vec_a = player_style_vectors[player_a].reshape(1, -1)
        vec_b = player_style_vectors[player_b].reshape(1, -1)
        style_sim = cosine_similarity(vec_a, vec_b)[0][0]
        print(f"Style similarity score: {style_sim:.2f} → measures complementary play style.")

        # Step 6e: Position-based baseline
        if total_matches_together == 0 and not common_history:
            pos_key = (player_positions[player_a], player_positions[player_b])
            pos_score = baseline_position_synergy.get(pos_key,
                        baseline_position_synergy.get((player_positions[player_b], player_positions[player_a]), 0.3))
            print(f"Players never played together → using position-based baseline synergy: {pos_score:.2f} "
                  f"({player_positions[player_a]} & {player_positions[player_b]})")
        else:
            pos_score = 0

        # Step 6f: Combine
        final_synergy = (weights['matches'] * match_score +
                         weights['individual_success'] * success_score +
                         weights['style'] * style_sim +
                         pos_score)
        print(f"Final synergy calculation:")
        print(f"  = (weight_matches * {match_score:.2f}) + (weight_individual_success * {success_score:.2f}) "
              f"+ (weight_style * {style_sim:.2f}) + baseline_pos {pos_score:.2f}")
        print(f"  => Final synergy for {player_a} & {player_b}: {final_synergy:.2f}")

        synergy_matrix.loc[player_a, player_b] = final_synergy
        synergy_matrix.loc[player_b, player_a] = final_synergy

    # Self synergy = 0 (to avoid bias in visualization)
    for p in team_players:
        synergy_matrix.loc[p, p] = 1.0

    print("\n" + "="*60)
    print("=== EXPLANATORY SYNERGY CALCULATION COMPLETE ===")
    print("="*60)
    return synergy_matrix


# --- Example execution ---
if __name__ == "__main__":
    import sys
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "optimal_kabaddi_team_ILP.csv"
    output_csv = sys.argv[2] if len(sys.argv) > 2 else "final_team_explanatory_synergy_matrix.csv"

    player_stats = pd.read_csv("datasets/player_statistics_all_seasons.csv")
    match_results = pd.read_csv("datasets/DS_match_modified.csv")
    events = pd.read_csv("datasets/DS_event_with_timestamps_clean2.csv")
    optimal_team = pd.read_csv(csv_file)

    my_team = optimal_team['player_name'].tolist()

    synergy_df = create_explanatory_synergy_matrix(my_team, player_stats, match_results, events)

    print("\nFinal Explanatory Synergy Matrix:")
    print(synergy_df)

    synergy_df.to_csv(output_csv)
    print(f"\nSaved to {output_csv}")
