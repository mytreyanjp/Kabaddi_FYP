import streamlit as st
import pandas as pd

@st.cache_data
def load_data():
    """
    Loads all required CSV files into DataFrames.
    Uses caching to avoid reloading on every rerun.
    """
    try:
        # Load the primary dataset which contains player stats and position info.
        players_df = pd.read_csv('processed_kabaddi_stats.csv')

        # Standardize column names for consistency
        players_df.columns = players_df.columns.str.lower()
        
        # Ensure player names are consistent (e.g., lowercase)
        players_df['player_name'] = players_df['player_name'].str.lower()
        
        # Handle players with multiple positions by taking the first one
        players_df['main_position'] = players_df['position_name'].apply(lambda x: x.split(',')[0].strip() if pd.notnull(x) else 'Unknown')
        
        return players_df
    except FileNotFoundError as e:
        st.error(f"Error: Required file not found. Please ensure the CSV files are uploaded: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during data loading: {e}")
        return None

def generate_why_text(row):
    """
    Generates a descriptive reason for a player being a top candidate based on their stats.
    This function has been adapted to use the columns available in the provided CSV file.
    """
    contributions = []
    # Check for significant stats using a simple points threshold for each category
    if row.get('raid_points', 0) > 200:
        contributions.append(f"a high number of raid points ({int(row['raid_points'])})")
    if row.get('tackle_points', 0) > 50:
        contributions.append(f"a strong performance in tackle points ({int(row['tackle_points'])})")
    if row.get('super_raids', 0) > 5:
        contributions.append("numerous super raids")
    if row.get('successful_raids', 0) > 100:
        contributions.append("a high volume of successful raids")
    if row.get('super_tackles', 0) > 5:
        contributions.append("excellent super tackle abilities")
    if row.get('do_or_die_points', 0) > 20:
        contributions.append("a clutch player in do-or-die raids")

    if contributions:
        return f"A top candidate due to {', '.join(contributions)}."
    else:
        return "A solid player with a good overall performance record."

# --- Streamlit UI Components ---

def main():
    st.set_page_config(page_title="Kabaddi Team Builder", layout="wide")
    st.markdown("""
        <style>
            .stApp {
                background-color: #0d1117;
                color: #c9d1d9;
            }
            .st-emotion-cache-1wv9v3w a {
                color: #2e8b57 !important;
            }
            .st-emotion-cache-1wv9v3w a:hover {
                text-decoration: underline;
            }
            .st-emotion-cache-6q9sum a {
                color: #2e8b57 !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("Kabaddi Team Builder")
    st.markdown("### Identify and evaluate top player candidates by role.")

    players_df = load_data()

    if players_df is not None:
        roles = sorted(players_df['main_position'].unique())
        
        selected_role = st.selectbox("Select a Player Role:", roles)
        
        if selected_role:
            st.header(f"Top {selected_role} Candidates")
            
            # Filter players by the selected role and sort by total_points as a skill score proxy
            filtered_players = players_df[players_df['main_position'] == selected_role].sort_values(by='total_points', ascending=False)
            
            if filtered_players.empty:
                st.info(f"No players found for the '{selected_role}' role.")
            else:
                for index, player in filtered_players.head(5).iterrows():
                    with st.container(border=True):
                        col1, col2 = st.columns([1, 2])
                        
                        with col1:
                            st.markdown(f"**<span style='color: #2e8b57; font-size: 24px;'>{player['player_name'].title()}</span>**", unsafe_allow_html=True)
                            st.markdown(f"Season: **{int(player['season'])}**")
                            st.markdown(f"Position: **{player['position_name']}**")
                            st.metric(label="Total Points", value=f"{player['total_points']:.0f}")

                        with col2:
                            st.markdown(f"### Why they're a top candidate:")
                            st.markdown(f"<p>{generate_why_text(player)}</p>", unsafe_allow_html=True)
                            
                            st.markdown("---")
                            
                            st.markdown("### Key Statistics")
                            
                            stat_cols = st.columns(3)
                            stats = {
                                'Raid Points': player.get('raid_points', 0),
                                'Tackle Points': player.get('tackle_points', 0),
                                'Successful Raids': player.get('successful_raids', 0),
                                'Successful Tackles': player.get('successful_tackles', 0),
                                'Super Raids': player.get('super_raids', 0),
                                'Super Tackles': player.get('super_tackles', 0)
                            }
                            
                            i = 0
                            for stat_name, stat_value in stats.items():
                                if pd.notnull(stat_value):
                                    with stat_cols[i % 3]:
                                        st.metric(label=stat_name, value=f"{stat_value:.0f}")
                                    i += 1
                                    
if __name__ == "__main__":
    main()
