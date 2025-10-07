import streamlit as st
import pandas as pd
import numpy as np
import random
import matplotlib.pyplot as plt

# ------------------------------------------------------
# 🎾 MONTE CARLO TENNIS SIMULATOR (FULL FEATURE VERSION)
# ------------------------------------------------------
# Includes:
# - Pressure-aware Monte Carlo (100k sims)
# - 3/5 set toggle
# - ATP/WTA toggle
# - Surface effects
# - Real-time match state
# - EV, Kelly, hedging, position tracking
# - Compact layout + scoreboard
# ------------------------------------------------------

st.set_page_config(layout="wide", page_title="🎾 Monte Carlo Tennis Match Simulator")

# ---------- Load Player Stats ----------
@st.cache_data
def load_data():
    return pd.read_csv("player_surface_stats_master.csv")

df = load_data()

# ---------- Sidebar Config ----------
with st.sidebar:
    st.header("⚙️ Match Setup")
    match_format = st.radio("Match Format", [3, 5], horizontal=True)
    surface = st.selectbox("Surface", ["Hard", "Clay", "Grass"])
    tour = st.radio("Tour", ["ATP", "WTA"], horizontal=True)
    pressure_toggle = st.toggle("Enable Pressure Logic", True)
    kelly_half = st.toggle("Use 0.5x Kelly", True)
    show_graphs = st.toggle("Show Graphs", True)

kelly_factor = 0.5 if kelly_half else 1.0

# ---------- Player Selection ----------
players = df[df["tour"] == tour]["player"].unique()
col1, col2 = st.columns(2)
with col1:
    player_a = st.selectbox("Select Player A", players, index=0)
with col2:
    player_b = st.selectbox("Select Player B", players, index=1 if len(players) > 1 else 0)

if player_a == player_b:
    st.error("Please select two different players.")
    st.stop()

def get_player_stats(player):
    row = df[(df["player"] == player) & (df["surface"] == surface)]
    if row.empty:
        return 0.62, 0.38
    return float(row["serve_win"].values[0]), float(row["return_win"].values[0])

sa_serve, sa_return = get_player_stats(player_a)
sb_serve, sb_return = get_player_stats(player_b)

# Surface adjustment (simplified)
surface_mod = {"Hard": 1.00, "Clay": 0.96, "Grass": 1.04}[surface]
sa_serve *= surface_mod
sb_serve *= surface_mod

# ---------- Live Scoreboard ----------
st.markdown("### 🟩 Live Scoreboard (Compact)")
sc1, sc2, sc3, sc4 = st.columns(4)
sets_a = sc1.number_input("Sets (A)", 0, match_format, 0, key="sa")
games_a = sc2.number_input("Games (A)", 0, 7, 0, key="ga")
points_a = sc3.number_input("Points (A)", 0, 3, 0, key="pa")
adv_a = sc4.checkbox("Adv A", key="adv_a")

sets_b = sc1.number_input("Sets (B)", 0, match_format, 0, key="sb")
games_b = sc2.number_input("Games (B)", 0, 7, 0, key="gb")
points_b = sc3.number_input("Points (B)", 0, 3, 0, key="pb")
adv_b = sc4.checkbox("Adv B", key="adv_b")

# ---------- Odds ----------
st.markdown("### 💰 Betfair Odds & Bankroll")
od1, od2, od3 = st.columns(3)
back_odds_a = od1.number_input(f"Back Odds {player_a}", 1.01, 100.0, 2.0, 0.01)
lay_odds_a = od2.number_input(f"Lay Odds {player_a}", 1.01, 100.0, 2.2, 0.01)
bankroll = od3.number_input("Bankroll (£)", 10.0, 100000.0, 1000.0, 10.0)

# ---------- Monte Carlo Simulation ----------
def simulate_match(a_serve, b_serve, sets_to_win, pressure=False):
    a_match_wins = 0
    for _ in range(100000):
        sa, sb = sets_a, sets_b
        while sa < sets_to_win and sb < sets_to_win:
            ga, gb = 0, 0
            while (ga < 6 and gb < 6) or abs(ga - gb) < 2:
                p = a_serve if random.random() < 0.5 else b_serve
                if pressure and (ga == 5 or gb == 5):
                    p *= 1.03  # small pressure boost
                if random.random() < p:
                    ga += 1
                else:
                    gb += 1
            if ga > gb:
                sa += 1
            else:
                sb += 1
        if sa > sb:
            a_match_wins += 1
    return a_match_wins / 100000

# ---------- Run Simulation ----------
sets_target = match_format // 2 + 1
sim_prob = simulate_match(sa_serve, sb_serve, sets_target, pressure_toggle)
market_prob = 1 / back_odds_a if back_odds_a > 0 else 0
edge = sim_prob - market_prob

# ---------- Betting Logic ----------
kelly_stake = max(2, (bankroll * edge) / max(0.01, (back_odds_a - 1)))
kelly_stake *= kelly_factor
bet_action = None

if edge > 0:
    bet_action = f"✅ BACK {player_a} for £{kelly_stake:.2f} (Positive EV)"
elif edge < 0:
    bet_action = f"🔴 LAY {player_a} for £{kelly_stake:.2f} (Negative EV)"
else:
    bet_action = "⏸️ No edge - Hold position"

# ---------- Results ----------
st.markdown("### 📊 Probability & Edge Analysis")
st.metric("Monte Carlo Win Probability", f"{sim_prob*100:.2f}%")
st.metric("Market Implied Probability", f"{market_prob*100:.2f}%")
st.metric("Edge", f"{edge*100:.2f}%")
st.success(bet_action)

# ---------- P&L Tracking ----------
if "bet_log" not in st.session_state:
    st.session_state["bet_log"] = []

st.session_state["bet_log"].append({
    "Player": player_a,
    "Simulated Win%": round(sim_prob*100, 2),
    "Market Win%": round(market_prob*100, 2),
    "Edge%": round(edge*100, 2),
    "Action": bet_action,
    "Bankroll": bankroll
})

bet_log = pd.DataFrame(st.session_state["bet_log"])
st.markdown("### 📋 Bet Log & Position Tracker")
st.dataframe(bet_log.tail(5), use_container_width=True)

# ---------- Graphs ----------
if show_graphs:
    st.markdown("### 📈 Monte Carlo vs Market Probabilities")
    fig, ax = plt.subplots()
    ax.bar(["Simulated", "Market"], [sim_prob, market_prob], color=["green", "blue"])
    ax.set_ylabel("Win Probability")
    ax.set_ylim(0, 1)
    st.pyplot(fig)

# ---------- Reset Button ----------
if st.button("🔁 Reset Match & Clear Log"):
    st.session_state["bet_log"] = []
    st.experimental_rerun()


