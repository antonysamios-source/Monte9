# =========================================================
# 🎾  MONTE CARLO TENNIS MATCH SIMULATOR – v11 (FULL BUILD)
# =========================================================
#  Includes:
#   - Fixed column mapping order (no KeyError)
#   - 3/5 set engine, pressure-aware Monte Carlo
#   - Kelly staking, EV logic, £2 minimum
#   - Auto header detection
#   - Back/Lay logic, position log
#   - EV progress bar, compact UI
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import random
import matplotlib.pyplot as plt

st.set_page_config(page_title="🎾 Monte Carlo Tennis Simulator", layout="wide")

# ---------------------------------------------------------
# 🧭 Utility: Detect column names dynamically
# ---------------------------------------------------------
def detect_columns(df: pd.DataFrame):
    cols = [c.lower() for c in df.columns]
    serve_col = next((c for c in cols if "serve" in c and ("win" in c or "point" in c)), None)
    ret_col = next((c for c in cols if "return" in c and ("win" in c or "point" in c)), None)
    surf_col = next((c for c in cols if "surface" in c), None)
    tour_col = next((c for c in cols if "tour" in c), None)
    player_col = next((c for c in cols if "player" in c), None)
    return {
        "player": player_col or "player",
        "tour": tour_col or "tour",
        "surface": surf_col or "surface",
        "serve": serve_col or "serve_win",
        "return": ret_col or "return_win",
    }

# ---------------------------------------------------------
# 🧩 Load Player Stats (cached)
# ---------------------------------------------------------
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("player_surface_stats_master.csv")
        df.columns = [c.lower() for c in df.columns]  # FIX moved earlier
        mapping = detect_columns(df)
        return df, mapping
    except Exception as e:
        st.error(f"❌ Could not load CSV: {e}")
        st.stop()

df, mapping = load_data()

# ---------------------------------------------------------
# ⚙️ Sidebar Controls
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Match Setup")
    match_format = st.radio("Match Format", [3, 5], horizontal=True)
    surface = st.selectbox("Surface", ["Hard", "Clay", "Grass"])
    tour = st.radio("Tour", ["ATP", "WTA"], horizontal=True)
    pressure_toggle = st.toggle("Enable Pressure Logic", True)
    kelly_half = st.toggle("Use 0.5x Kelly", True)
    show_graphs = st.toggle("Show Graphs", True)

kelly_factor = 0.5 if kelly_half else 1.0

# ---------------------------------------------------------
# 🧍 Player Selection
# ---------------------------------------------------------
players = df[df[mapping["tour"]] == tour][mapping["player"]].unique()
col1, col2 = st.columns(2)
with col1:
    player_a = st.selectbox("Select Player A", players, index=0)
with col2:
    player_b = st.selectbox("Select Player B", players, index=1 if len(players) > 1 else 0)
if player_a == player_b:
    st.warning("Please select two different players.")
    st.stop()

# ---------------------------------------------------------
# 🎯 Extract Player Stats Safely
# ---------------------------------------------------------
def get_player_stats(player):
    row = df[(df[mapping["player"]] == player) & (df[mapping["surface"]] == surface)]
    if row.empty:
        return 0.62, 0.38
    try:
        serve = float(row[mapping["serve"]].values[0])
        ret = float(row[mapping["return"]].values[0])
    except Exception:
        serve, ret = 0.62, 0.38
    return serve, ret

sa_serve, sa_return = get_player_stats(player_a)
sb_serve, sb_return = get_player_stats(player_b)

# Apply surface multiplier
surf_mult = {"Hard": 1.00, "Clay": 0.96, "Grass": 1.04}[surface]
sa_serve *= surf_mult
sb_serve *= surf_mult

# ---------------------------------------------------------
# 🟩 Compact Scoreboard
# ---------------------------------------------------------
st.markdown("### 🟩 Live Scoreboard (Compact)")
s1, s2, s3, s4 = st.columns(4)
sets_a = s1.number_input("Sets (A)", 0, match_format, 0)
games_a = s2.number_input("Games (A)", 0, 7, 0)
points_a = s3.number_input("Pts (A)", 0, 3, 0)
adv_a = s4.checkbox("Adv A")

sets_b = s1.number_input("Sets (B)", 0, match_format, 0)
games_b = s2.number_input("Games (B)", 0, 7, 0)
points_b = s3.number_input("Pts (B)", 0, 3, 0)
adv_b = s4.checkbox("Adv B")

# ---------------------------------------------------------
# 💰 Odds & Bankroll
# ---------------------------------------------------------
st.markdown("### 💰 Betfair Odds & Bankroll")
o1, o2, o3 = st.columns(3)
back_odds_a = o1.number_input(f"Back Odds {player_a}", 1.01, 100.0, 2.0, 0.01)
lay_odds_a = o2.number_input(f"Lay Odds {player_a}", 1.01, 100.0, 2.2, 0.01)
bankroll = o3.number_input("Bankroll (£)", 10.0, 100000.0, 1000.0, 10.0)

# ---------------------------------------------------------
# 🧮 Monte Carlo Simulation (Pressure-Aware)
# ---------------------------------------------------------
def simulate_match(a_serve, b_serve, sets_to_win, pressure=False):
    a_match_wins = 0
    for _ in range(100000):
        sa, sb = sets_a, sets_b
        while sa < sets_to_win and sb < sets_to_win:
            ga, gb = 0, 0
            while (ga < 6 and gb < 6) or abs(ga - gb) < 2:
                p = a_serve if random.random() < 0.5 else b_serve
                if pressure and (ga >= 5 or gb >= 5):
                    p *= 1.03
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

sets_target = match_format // 2 + 1
sim_prob = simulate_match(sa_serve, sb_serve, sets_target, pressure_toggle)
market_prob = 1 / back_odds_a if back_odds_a > 0 else 0
edge = sim_prob - market_prob

# ---------------------------------------------------------
# 📈 Betting Logic + EV Progress Bar
# ---------------------------------------------------------
kelly_stake = max(2, (bankroll * edge) / max(0.01, (back_odds_a - 1)))
kelly_stake *= kelly_factor
if edge > 0:
    action = f"✅ BACK {player_a} £{kelly_stake:.2f}"
elif edge < 0:
    action = f"🔴 LAY {player_a} £{kelly_stake:.2f}"
else:
    action = "⏸ No Edge"

st.markdown("### 📊 Probability & Edge Analysis")
st.metric("Monte Carlo Win Prob", f"{sim_prob*100:.2f}%")
st.metric("Market Implied Prob", f"{market_prob*100:.2f}%")
st.metric("Edge", f"{edge*100:.2f}%")
progress = min(max((edge * 100) + 50, 0), 100)
st.progress(progress / 100)
st.success(action)

# ---------------------------------------------------------
# 💹 P&L Tracking
# ---------------------------------------------------------
if "bet_log" not in st.session_state:
    st.session_state["bet_log"] = []

st.session_state["bet_log"].append({
    "Player": player_a,
    "Sim Win%": round(sim_prob * 100, 2),
    "Market Win%": round(market_prob * 100, 2),
    "Edge%": round(edge * 100, 2),
    "Action": action,
    "Bankroll": bankroll,
})
log_df = pd.DataFrame(st.session_state["bet_log"])
st.markdown("### 📋 Recent Bets")
st.dataframe(log_df.tail(5), use_container_width=True)

# ---------------------------------------------------------
# 📈 Graphs
# ---------------------------------------------------------
if show_graphs:
    st.markdown("### 📈 Sim vs Market Probabilities")
    fig, ax = plt.subplots()
    ax.bar(["Simulated", "Market"], [sim_prob, market_prob], color=["green", "blue"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Win Probability")
    st.pyplot(fig)

# ---------------------------------------------------------
# 🔁 Reset
# ---------------------------------------------------------
if st.button("🔁 Reset Match / Clear Log"):
    st.session_state["bet_log"] = []
    st.experimental_rerun()

# ✅ End — ~175 lines




