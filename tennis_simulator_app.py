import streamlit as st
import pandas as pd
import numpy as np
import random

# === PAGE CONFIG ===
st.set_page_config(page_title="🎾 Monte Carlo Tennis Match Simulator", layout="wide")

# === LOAD DATA ===
@st.cache_data
def load_data():
    df = pd.read_csv("player_surface_stats_master.csv")
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df

stats_df = load_data()

# === UI LAYOUT ===
st.markdown("## 🎾 Monte Carlo Tennis Match Simulator")
col1, col2, col3 = st.columns(3)

with col1:
    match_format = st.radio("Match Format", ["3", "5"], horizontal=True)
with col2:
    surface = st.selectbox("Surface", ["Hard", "Clay", "Grass"])
with col3:
    tour = st.radio("Tour", ["ATP", "WTA"], horizontal=True)

players = stats_df["player"].unique()
player_a = st.selectbox("Select Player A", players, index=0)
player_b = st.selectbox("Select Player B", players, index=1)

# === SCOREBOARD UI ===
st.markdown("### 🟩 Live Scoreboard")
score_a, score_b = st.columns(2)
with score_a:
    sets_a = st.number_input("Sets Won (A)", 0, 5, 0, 1)
    games_a = st.number_input("Games in Current Set (A)", 0, 7, 0, 1)
    points_a = st.number_input("Points (A)", 0, 4, 0, 1)
with score_b:
    sets_b = st.number_input("Sets Won (B)", 0, 5, 0, 1)
    games_b = st.number_input("Games in Current Set (B)", 0, 7, 0, 1)
    points_b = st.number_input("Points (B)", 0, 4, 0, 1)

# === ODDS & STAKING ===
st.markdown("### 💰 Odds & Betting Setup")
col_odds = st.columns(4)
with col_odds[0]:
    back_odds_a = st.number_input(f"Back Odds for {player_a}", value=2.0, step=0.01)
with col_odds[1]:
    lay_odds_a = st.number_input(f"Lay Odds for {player_a}", value=2.2, step=0.01)
with col_odds[2]:
    back_odds_b = st.number_input(f"Back Odds for {player_b}", value=2.1, step=0.01)
with col_odds[3]:
    lay_odds_b = st.number_input(f"Lay Odds for {player_b}", value=2.3, step=0.01)

bankroll = st.number_input("💵 Bankroll", value=1000.0, step=10.0)
kelly_fraction = st.slider("Kelly Multiplier", 0.1, 1.0, 0.5)
pressure_on = st.toggle("Pressure Logic", value=True)

# === HELPERS ===
def get_player_stats(player_name):
    row = stats_df[(stats_df["player"] == player_name) & (stats_df["surface"] == surface.lower())]
    if row.empty:
        return 0.65, 0.35
    return float(row["serve_win"].values[0]), float(row["return_win"].values[0])

def calculate_pressure_multiplier(points_a, points_b):
    # Adjust multiplier based on pressure
    if pressure_on and (points_a == 30 and points_b == 40 or points_b == 30 and points_a == 40):
        return 1.1  # simulate pressure effect
    return 1.0

def monte_carlo_sim(sa_serve, sa_return, sb_serve, sb_return):
    wins = 0
    total = 100_000
    for _ in range(total):
        prob = random.random()
        if prob < sa_serve * calculate_pressure_multiplier(points_a, points_b):
            wins += 1
    return wins / total

# === GET STATS ===
sa_serve, sa_return = get_player_stats(player_a)
sb_serve, sb_return = get_player_stats(player_b)

# === SIMULATION ===
sim_prob_a = monte_carlo_sim(sa_serve, sa_return, sb_serve, sb_return)
sim_prob_b = 1 - sim_prob_a

# === IMPLIED PROBABILITIES ===
implied_prob_a = 1 / back_odds_a
implied_prob_b = 1 / back_odds_b

edge_a = sim_prob_a - implied_prob_a
edge_b = sim_prob_b - implied_prob_b

stake_a = max(2, bankroll * edge_a * kelly_fraction)
stake_b = max(2, bankroll * edge_b * kelly_fraction)

# === DISPLAY RESULTS ===
st.markdown("### 📈 Simulation Results")
col_sim = st.columns(2)
with col_sim[0]:
    st.metric(f"Win Probability: {player_a}", f"{sim_prob_a*100:.2f}%")
    st.metric("Market Implied", f"{implied_prob_a*100:.2f}%")
    st.metric("Edge", f"{edge_a*100:.2f}%")
    st.metric("Stake (£)", f"{stake_a:.2f}")
with col_sim[1]:
    st.metric(f"Win Probability: {player_b}", f"{sim_prob_b*100:.2f}%")
    st.metric("Market Implied", f"{implied_prob_b*100:.2f}%")
    st.metric("Edge", f"{edge_b*100:.2f}%")
    st.metric("Stake (£)", f"{stake_b:.2f}")

# === TRADE LOG ===
st.markdown("### 🧾 P&L Log (Coming Soon...)")
st.info("This section will track open positions, profit/loss, hedging, and cut-outs.")






