import streamlit as st
import pandas as pd
import numpy as np
import random
import time

# ==============================
# APP CONFIG & DATA LOAD
# ==============================
st.set_page_config(page_title="🎾 Monte Carlo Tennis Simulator", layout="wide")

@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/antonysamios-source/Monte10/main/player_surface_stats_master.csv"
    df = pd.read_csv(url)
    df.columns = df.columns.str.lower()
    return df

df = load_data()

# ==============================
# HELPER FUNCTIONS
# ==============================
def get_player_stats(player, surface, tour):
    row = df[(df["player"] == player) & (df["surface"] == surface) & (df["tour"] == tour)]
    if row.empty:
        return 0.65, 0.35
    return float(row["serve_win"].values[0]), float(row["return_win"].values[0])

def kelly_stake(prob, odds, bankroll, half=False):
    edge = (prob * odds - 1) / (odds - 1)
    stake = bankroll * edge
    if half:
        stake *= 0.5
    return max(stake, 2.0) if edge > 0 else 0.0

def pressure_adjust(p, state, pressure_on):
    if not pressure_on:
        return p
    if "break" in state or "set" in state or "match" in state:
        return min(p * 1.03, 0.99)
    return p

# ==============================
# UI: COMPACT LAYOUT
# ==============================
col1, col2, col3 = st.columns([1,1,1])

with col1:
    st.markdown("### ⚙️ Match Settings")
    format_choice = st.radio("Match Format", ["3", "5"], horizontal=True)
    surface = st.selectbox("Surface", ["Hard", "Clay", "Grass"])
    tour = st.radio("Tour", ["ATP", "WTA"], horizontal=True)
    pressure_on = st.checkbox("Pressure Logic ON", value=True)

with col2:
    st.markdown("### 🎾 Player Selection")
    players = sorted(df["player"].unique())
    player_a = st.selectbox("Player A", options=players, index=0, key="a")
    player_b = st.selectbox("Player B", options=players, index=1 if len(players) > 1 else 0, key="b")

with col3:
    st.markdown("### 💰 Betting Setup")
    odds_a = st.number_input(f"Back Odds {player_a}", value=2.0, step=0.01, key="odds_a")
    odds_b = st.number_input(f"Back Odds {player_b}", value=2.0, step=0.01, key="odds_b")
    bankroll = st.number_input("Your Bankroll (£)", value=1000.0, step=50.0)
    half_kelly = st.checkbox("Use 0.5 Kelly", value=False)

# ==============================
# SCOREBOARD COMPACT VIEW
# ==============================
st.markdown("### 🟩 Live Scoreboard (Compact)")

score_col1, score_col2, score_col3, score_col4 = st.columns(4)
with score_col1:
    sets_a = st.number_input(f"{player_a} Sets", value=0, step=1)
    games_a = st.number_input(f"{player_a} Games", value=0, step=1)
    points_a = st.number_input(f"{player_a} Points", value=0, step=1)
with score_col2:
    sets_b = st.number_input(f"{player_b} Sets", value=0, step=1)
    games_b = st.number_input(f"{player_b} Games", value=0, step=1)
    points_b = st.number_input(f"{player_b} Points", value=0, step=1)
with score_col3:
    server = st.radio("Who is Serving?", [player_a, player_b], horizontal=True)
with score_col4:
    run_sim = st.button("▶️ Run Simulation")
    reset = st.button("🔁 Reset Match")

# ==============================
# MONTE CARLO SIMULATION (Huang-based)
# ==============================
def simulate_match_state(a_sv, b_sv, a_rt, b_rt, sets_a, sets_b, games_a, games_b, points_a, points_b, best_of, server, pressure_on):
    total_runs = 100000
    wins_a = 0
    sets_to_win = int(best_of)//2 + 1
    for _ in range(total_runs):
        sA, sB, gA, gB, pA, pB = sets_a, sets_b, games_a, games_b, points_a, points_b
        serv = server
        while sA < sets_to_win and sB < sets_to_win:
            if serv == player_a:
                p_win = pressure_adjust(a_sv, "normal", pressure_on)
            else:
                p_win = pressure_adjust(1 - b_rt, "normal", pressure_on)
            if random.random() < p_win:
                pA += 1
            else:
                pB += 1
            # Handle game logic
            if pA >= 4 and pA - pB >= 2:
                gA += 1
                pA, pB = 0, 0
                serv = player_b if serv == player_a else player_a
            elif pB >= 4 and pB - pA >= 2:
                gB += 1
                pA, pB = 0, 0
                serv = player_b if serv == player_a else player_a
            # Handle set logic
            if gA >= 6 and gA - gB >= 2:
                sA += 1
                gA, gB = 0, 0
            elif gB >= 6 and gB - gA >= 2:
                sB += 1
                gA, gB = 0, 0
        if sA > sB:
            wins_a += 1
    return wins_a / total_runs

# ==============================
# RUN SIMULATION
# ==============================
if run_sim:
    sa_serve, sa_return = get_player_stats(player_a, surface, tour)
    sb_serve, sb_return = get_player_stats(player_b, surface, tour)
    st.write("⏳ Running Monte Carlo simulation...")
    progress = st.progress(0)
    probA = simulate_match_state(sa_serve, sb_serve, sa_return, sb_return,
                                 sets_a, sets_b, games_a, games_b, points_a, points_b,
                                 format_choice, server, pressure_on)
    for i in range(100):
        time.sleep(0.005)
        progress.progress(i + 1)
    st.success("✅ Simulation Complete!")

    # Convert to implied odds
    implied_odds = 1 / probA if probA > 0 else 999
    market_prob_a = 1 / odds_a
    ev_a = probA - market_prob_a
    stake = kelly_stake(probA, odds_a, bankroll, half_kelly)
    potential_profit = stake * (odds_a - 1) * 0.95 if ev_a > 0 else -stake

    st.markdown(f"""
    ### 📊 Results
    - **{player_a} Win Probability:** {probA*100:.2f}%
    - **Market Implied Probability:** {market_prob_a*100:.2f}%
    - **Expected Value:** {ev_a*100:.2f}%
    - **Recommended Stake:** £{stake:.2f}
    - **Projected Profit/Loss:** £{potential_profit:.2f}
    """)

# ==============================
# FOOTER
# ==============================
st.markdown("---")
st.markdown("Built on Huang (2011) Tennis Markov Model • 100,000 Monte Carlo Iterations • © Monte10")



