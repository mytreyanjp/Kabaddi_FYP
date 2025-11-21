import os
import pandas as pd
import streamlit as st
import plotly.express as px
import difflib

# --- CONFIG ---
PATTERNS_FOLDER = r"PlayerRaids"
INSIGHT_FILE = r"PlayerRaids\player_vs_team_insights.csv"
NLP_FOLDER = r"reports"

# --- LOAD INSIGHTS ---
insights = pd.read_csv(INSIGHT_FILE)

st.set_page_config(page_title="Kabaddi Tactical Dashboard", layout="wide")
st.title(" Kabaddi Tactical Intelligence Dashboard")

# --- PLAYER SELECTION ---
players = sorted(insights['raider'].unique())
selected_player = st.selectbox(" Select Raider", players)
player_data = insights[insights['raider'] == selected_player]

# --- TEAM SELECTION ---
teams = sorted(player_data['opponent'].unique())
selected_team = st.selectbox(" Select Opponent Team", teams)

# --- OVERVIEW METRICS ---
st.markdown("###  Player Overview")
col1, col2, col3 = st.columns(3)
col1.metric("Total Raids", int(player_data['n_events'].sum()))
col2.metric("Average Success Rate", f"{player_data['success_rate'].mean():.2%}")
col3.metric("Avg Points / Raid", f"{player_data['avg_points_per_raid'].mean():.2f}")

# --- BAR: Success Rate vs Teams ---
st.markdown(f"###  {selected_player} - Success Rate vs All Teams")
fig_bar = px.bar(
    player_data,
    x='opponent',
    y='success_rate',
    color='success_rate',
    text='success_rate',
    title=f"{selected_player} - Success Rate vs Teams",
    color_continuous_scale='Viridis'
)
fig_bar.update_traces(texttemplate='%{text:.2f}', textposition='outside')
fig_bar.update_layout(xaxis_title="Opponent Team", yaxis_title="Success Rate", xaxis_tickangle=-45)
st.plotly_chart(fig_bar, use_container_width=True)

# --- LINE: Avg Points per Raid ---
st.markdown(f"###  {selected_player} - Avg Points per Raid vs Teams")
fig_line = px.line(
    player_data,
    x='opponent',
    y='avg_points_per_raid',
    markers=True,
    title=f"{selected_player} - Avg Points per Raid vs Teams"
)
fig_line.update_layout(xaxis_title="Opponent Team", yaxis_title="Avg Points per Raid", xaxis_tickangle=-45)
st.plotly_chart(fig_line, use_container_width=True)

# --- TABLE: Detailed stats ---
st.markdown("### Detailed Stats")
st.dataframe(
    player_data[['opponent', 'n_events', 'success_rate', 'avg_points_per_raid',
                 'doordie_success_count', 'bonus_success_count', 'top_patterns']]
)

# --- NLP Report Loader ---
def find_nlp_report(player, team):
    player_key = player.replace(" ", "_")
    team_key = team.replace(" ", "_")
    reports = [f for f in os.listdir(NLP_FOLDER) if f.endswith("_report.md")]
    matches = [f for f in reports if player_key in f and team_key in f]
    if matches:
        return os.path.join(NLP_FOLDER, matches[0])
    # fallback: fuzzy match (handles naming variants)
    best_match = difflib.get_close_matches(f"{player_key}__{team_key}", reports, n=1)
    if best_match:
        return os.path.join(NLP_FOLDER, best_match[0])
    return None

# --- SHOW NLP Report ---
st.markdown("### Tactical Insights")
nlp_file = find_nlp_report(selected_player, selected_team)
if nlp_file and os.path.exists(nlp_file):
    with open(nlp_file, "r", encoding="utf-8") as f:
        report = f.read()
    st.markdown(report)
else:
    st.info(" No NLP report available for this player vs team.")

# --- PATTERN FILES ---
def find_pattern_file(player, team):
    player_key = player.replace(" ", "_")
    team_key = team.replace(" ", "_")
    pattern_files = [f for f in os.listdir(PATTERNS_FOLDER) if f.endswith(".csv")]
    candidates = [f for f in pattern_files if player_key in f]
    if not candidates:
        return None
    best_match = difflib.get_close_matches(team_key, candidates, n=1)
    if best_match:
        return os.path.join(PATTERNS_FOLDER, best_match[0])
    return None

