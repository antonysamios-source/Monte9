import streamlit as st
import pandas as pd
import numpy as np
import random

# Title
st.title("🎾 Monte Carlo Tennis Match Simulator (Monte9)")

# Sidebar: Config
st.sidebar.header("Match Settings")
best_of = st.sidebar.radio("Match Format", [3, 5], horizontal=True)
surface = st.sidebar.selectbox("Surface", ["Hard", "Clay", "Grass"])
tour = st.sidebar.radio("Tour", ["ATP", "WTA"], horizontal=True)
pressure_toggle = st.sidebar.checkbox("Enable Pressure-Aware Simulation", value=True)

# Load Data
@st.cache_data
def load_data():
    return pd.read_csv("player_surface_stats_master.csv")

stats_df = load_data()

# Ensure at least two players are available
available_players = sorted(stats_df["player"].unique())
default_player_a = available_players[0]
default_player_b = available_players[1] if len(available_players) > 1 else available_players[0]

# Player Selection
player_a = st.selectbox("Select Player A", available_players, index=0, key="a")
player_b = st.selectbox("Select Player B", available_players, index=1, key="b")

# Check if players are different
if player_a == player_b:
    st.warning("Please select two different players to simulate.")
    st.stop()

# Get Serve/Return Stats
def get_player_stats(player):
    row = stats_df[(stats_df["player"] == player) &
                   (stats_df["surface"] == surface) &
                   (stats_df["tour"] == tour)]
    if row.empty:
        st.error(f"No stats found for {player} on {surface} ({tour}).")
        st.stop()
    return float(row["serve_win"].values[0]), float(row["return_win"].values[0])

sa_serve, sa_return = get_player_stats(player_a)
sb_serve, sb_return = get_player_stats(player_b)

# Live Scoreboard (compact input grid)
st.markdown("### 🟩 Live Scoreboard")
col1, col2 = st.columns(2)
with col1:
    sets_a = st.number_input("Sets Won (A)", 0, best_of//2, step=1, key="sa")
    games_a = st.number_input("Games (A)", 0, 7, step=1, key="ga")
    points_a = st.number_input("Points (A)", 0, 4, step=1, key="pa")
with col2:
    sets_b = st.number_input("Sets Won (B)", 0, best_of//2, step=1, key="sb")
    games_b = st.number_input("Games (B)", 0, 7, step=1, key="gb")
    points_b = st.number_input("Points (B)", 0, 4, step=1, key="pb")

# Odds Input (compact)
st.markdown("### 💰 Odds & Betting Setup")
col3, col4 = st.columns(2)
with col3:
    odds_a = st.number_input("Back Odds for " + player_a, value=2.0, step=0.01, key="odds_a")
    lay_a = st.number_input("Lay Odds for " + player_a, value=2.2, step=0.01, key="lay_a")
with col4:
    odds_b = st.number_input("Back Odds for " + player_b, value=2.0, step=0.01, key="odds_b")
    lay_b = st.number_input("Lay Odds for " + player_b, value=2.2, step=0.01, key="lay_b")

bankroll = st.number_input("💵 Starting Bankroll (£)", value=1000.0, step=10.0)
use_half_kelly = st.checkbox("Use Half Kelly", value=False)

# Monte Carlo Simulation
def simulate_match(sa, sb, serve_win_a, return_win_a, serve_win_b, return_win_b):
    wins_a = 0
    iterations = 100000
    for _ in range(iterations):
        score_a, score_b = sa, sb
        games_a_sim, games_b_sim = games_a, games_b
        sets_to_win = best_of // 2 + 1
        while score_a < sets_to_win and score_b < sets_to_win:
            games_a_set, games_b_set = 0, 0
            while (games_a_set < 6 and games_b_set < 6) or abs(games_a_set - games_b_set) < 2:
                if random.random() < serve_win_a:
                    games_a_set += 1
                else:
                    games_b_set += 1
            if pressure_toggle and (games_a_set == 5 or games_b_set == 5):
                if random.random() < (serve_win_a * 1.05):
                    score_a += 1
                else:
                    score_b += 1
            else:
                if games_a_set > games_b_set:
                    score_a += 1
                else:
                    score_b += 1
        if score_a > score_b:
            wins_a += 1
    return wins_a / iterations

# Run simulation
win_prob = simulate_match(sets_a, sets_b, sa_serve, sa_return, sb_serve, sb_return)

# Display
st.subheader("📈 Match Win Probability")
st.write(f"{player_a}: **{win_prob*100:.2f}%**  |  {player_b}: **{(1-win_prob)*100:.2f}%**")

# EV + Kelly
def implied_prob(odds):
    return 1 / odds if odds > 0 else 0

ip_a = implied_prob(odds_a)
ip_b = implied_prob(odds_b)
edge_a = win_prob - ip_a
edge_b = (1 - win_prob) - ip_b

def kelly_fraction(p, b):
    return (p * (b + 1) - 1) / b if b > 0 else 0

stake = 0
side = ""
if edge_a > 0:
    k = kelly_fraction(win_prob, odds_a - 1)
    stake = max(2, (k / 2 if use_half_kelly else k) * bankroll)
    side = f"✅ Back {player_a}"
elif edge_b > 0:
    k = kelly_fraction(1 - win_prob, odds_b - 1)
    stake = max(2, (k / 2 if use_half_kelly else k) * bankroll)
    side = f"✅ Back {player_b}"

# Output
st.subheader("🎯 Suggested Bet")
if stake > 0:
    st.success(f"{side} | Stake: £{stake:.2f}")
else:
    st.info("No +EV bet found.")


