import streamlit as st
import numpy as np
import pandas as pd
import random

# Title
st.set_page_config(layout="wide")
st.title("🎾 Monte Carlo Tennis Match Simulator (Monte10)")

# Load player stats
@st.cache_data
def load_stats():
    return pd.read_csv("player_surface_stats_master.csv")

df = load_stats()

# Sidebar inputs
with st.sidebar:
    st.header("🎛️ Match Setup")
    match_format = st.radio("Match Format", [3, 5], horizontal=True)
    surface = st.selectbox("Surface", ["Hard", "Clay", "Grass"])
    tour = st.radio("Tour", ["ATP", "WTA"], horizontal=True)

    players = sorted(df["player"].unique())
    default_a = players[0]
    default_b = players[1] if players[1] != default_a else players[2]
    player_a = st.selectbox("Select Player A", players, index=players.index(default_a))
    player_b = st.selectbox("Select Player B", players, index=players.index(default_b))

# Get player stats
def get_player_stats(player):
    row = df[(df["player"] == player) & (df["surface"] == surface) & (df["tour"] == tour)]
    if row.empty:
        return 0.65, 0.35
    return float(row["serve_win"].values[0]), float(row["return_win"].values[0])

sa_serve, sa_return = get_player_stats(player_a)
sb_serve, sb_return = get_player_stats(player_b)

# Live Scoreboard
st.markdown("### 🟩 Live Scoreboard")
col1, col2, col3 = st.columns(3)
with col1:
    sets_a = st.number_input("Sets Won (A)", 0, match_format, 0, key="sets_a")
    games_a = st.number_input("Games (A)", 0, 7, 0, key="games_a")
    points_a = st.number_input("Points (A)", 0, 3, 0, key="points_a")
with col2:
    sets_b = st.number_input("Sets Won (B)", 0, match_format, 0, key="sets_b")
    games_b = st.number_input("Games (B)", 0, 7, 0, key="games_b")
    points_b = st.number_input("Points (B)", 0, 3, 0, key="points_b")
with col3:
    pressure_toggle = st.toggle("🔥 Pressure Points?", value=True)
    sets_needed = match_format // 2 + 1

# Betting Odds
st.markdown("### 💰 Odds & Trading Logic")
col4, col5, col6 = st.columns(3)
with col4:
    odds_back = st.number_input(f"Back Odds ({player_a})", value=2.00, step=0.01, key="odds_back")
with col5:
    odds_lay = st.number_input(f"Lay Odds ({player_a})", value=2.20, step=0.01, key="odds_lay")
with col6:
    kelly_toggle = st.toggle("Use 0.5x Kelly?", value=True)

bankroll = st.number_input("🏦 Starting Bankroll (£)", value=1000.00, step=10.00)

# Score to state
current_state = {
    "sets": [sets_a, sets_b],
    "games": [games_a, games_b],
    "points": [points_a, points_b]
}

# Monte Carlo Simulation
def simulate_match(p1_serve, p2_serve, state, best_of, pressure_on):
    p1_wins = 0
    sims = 100_000
    for _ in range(sims):
        sets_a, sets_b = state["sets"]
        games_a, games_b = state["games"]
        points_a, points_b = state["points"]
        while sets_a < sets_needed and sets_b < sets_needed:
            # Basic probability with optional pressure boost
            p_a = p1_serve
            p_b = 1 - p2_serve
            if pressure_on and (games_a == 5 or games_b == 5):
                p_a += 0.02
                p_b -= 0.02
            if random.random() < p_a:
                points_a += 1
            else:
                points_b += 1

            if points_a >= 4 and points_a - points_b >= 2:
                games_a += 1
                points_a, points_b = 0, 0
            elif points_b >= 4 and points_b - points_a >= 2:
                games_b += 1
                points_a, points_b = 0, 0

            if games_a >= 6 and games_a - games_b >= 2:
                sets_a += 1
                games_a, games_b = 0, 0
            elif games_b >= 6 and games_b - games_a >= 2:
                sets_b += 1
                games_a, games_b = 0, 0

        if sets_a >= sets_needed:
            p1_wins += 1
    return p1_wins / sims

win_prob = simulate_match(sa_serve, sb_serve, current_state, match_format, pressure_toggle)

# Implied probability from odds
implied_prob = 1 / odds_back if odds_back > 1 else 0
edge = win_prob - implied_prob

# EV Calculation
kelly_fraction = edge / (1 - odds_back) if edge > 0 else 0
kelly_fraction *= 0.5 if kelly_toggle else 1
stake = max(round(kelly_fraction * bankroll, 2), 2.00) if kelly_fraction > 0 else 0

# Output Section
st.markdown("### 📊 Results")
col7, col8, col9 = st.columns(3)
with col7:
    st.metric("Market Implied Win %", f"{implied_prob*100:.2f}%")
with col8:
    st.metric("Monte Carlo Win %", f"{win_prob*100:.2f}%")
with col9:
    st.metric("Recommended Stake", f"£{stake:.2f}" if stake > 0 else "No Bet")

# Log Bet (placeholder - can be extended to table)
if stake > 0:
    st.success(f"✅ Positive EV detected — Stake £{stake:.2f} on {player_a}")
else:
    st.warning("🟥 No +EV opportunity at current odds.")

# Graph placeholder
st.markdown("📈 Graphs and P&L tracking coming soon...")





