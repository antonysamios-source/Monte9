import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- Load player stats ---
@st.cache_data
def load_data():
    df = pd.read_csv("player_surface_stats_master.csv")
    return df

df = load_data()

# --- App Configuration ---
st.set_page_config(page_title="Monte Carlo Tennis Simulator", layout="centered")
st.title("🎾 Monte Carlo Tennis Match Simulator (Monte10)")

# --- UI Layout ---
col1, col2, col3 = st.columns(3)
with col1:
    match_format = st.radio("Match Format", ["Best of 3", "Best of 5"])
with col2:
    tour = st.radio("Tour", ["ATP", "WTA"])
with col3:
    surface = st.selectbox("Surface", ["Hard", "Clay", "Grass"])

best_of_sets = 3 if match_format == "Best of 3" else 5

filtered_df = df[(df["tour"] == tour) & (df["surface"] == surface)]
players = sorted(filtered_df["player"].unique())

col1, col2 = st.columns(2)
with col1:
    player_a = st.selectbox("Select Player A", players, index=0)
with col2:
    player_b = st.selectbox("Select Player B", players, index=1 if len(players) > 1 else 0)

if player_a == player_b:
    st.warning("Choose two different players.")
    st.stop()

# --- Get player stats ---
def get_stats(name):
    row = filtered_df[filtered_df["player"] == name]
    return float(row["serve_win_pct"].values[0]), float(row["return_win_pct"].values[0])

sa_serve, sa_return = get_stats(player_a)
sb_serve, sb_return = get_stats(player_b)

# --- Scoreboard ---
st.markdown("#### 🟩 Live Scoreboard")
sc1, sc2 = st.columns(2)
with sc1:
    sets_a = st.number_input("Sets A", min_value=0, max_value=best_of_sets, value=0)
    games_a = st.number_input("Games A", min_value=0, max_value=6, value=0)
    points_a = st.number_input("Points A", min_value=0, max_value=3, value=0)
with sc2:
    sets_b = st.number_input("Sets B", min_value=0, max_value=best_of_sets, value=0)
    games_b = st.number_input("Games B", min_value=0, max_value=6, value=0)
    points_b = st.number_input("Points B", min_value=0, max_value=3, value=0)

# --- Betting Setup ---
st.markdown("#### 💰 Odds & EV")
odds1, odds2 = st.columns(2)
with odds1:
    back_odds_a = st.number_input(f"Back Odds {player_a}", value=2.0)
    lay_odds_a = st.number_input(f"Lay Odds {player_a}", value=2.2)
with odds2:
    back_odds_b = st.number_input(f"Back Odds {player_b}", value=2.0)
    lay_odds_b = st.number_input(f"Lay Odds {player_b}", value=2.2)

kelly_toggle = st.radio("Stake Strategy", ["Full Kelly", "Half Kelly"])
bankroll = st.number_input("Bankroll (£)", min_value=2, value=100)

# --- Sim Functions ---
def est_prob(sa, sr, sb, rr, sa_set, sa_game, sb_set, sb_game, pressure=True):
    base_prob = sa * (1 - rr)
    adj = 0.02 if pressure and sb_game >= 4 else 0
    prob = 0.5 + (base_prob - sb * (1 - sr)) / 200 + adj + (sa_set - sb_set) * 0.1
    return max(0.01, min(0.99, prob))

def monte(prob, n=100000):
    return np.mean(np.random.rand(n) < prob)

def ev(prob, odds):
    return (prob * (odds - 1)) - (1 - prob)

def kelly(prob, odds, roll, k_frac=1.0):
    edge = ev(prob, odds)
    if edge <= 0:
        return 0
    stake = roll * ((odds * prob - (1 - prob)) / (odds - 1)) * k_frac
    return max(2, min(roll, stake))

# --- Position & Log Tracking ---
pnl_log = []
sim_points = 100000

if st.button("🎯 Simulate Match & Recommend Bets"):
    prob_a = est_prob(sa_serve, sa_return, sb_serve, sb_return, sets_a, games_a, sets_b, games_b)
    prob_b = 1 - prob_a

    sim_a = monte(prob_a, sim_points)
    sim_b = 1 - sim_a

    st.markdown("### 📊 Results")
    ca, cb = st.columns(2)

    kf = 0.5 if kelly_toggle == "Half Kelly" else 1

    with ca:
        st.write(f"**{player_a} Win %:** {sim_a:.2%}")
        st.write(f"Back Implied: {1/back_odds_a:.2%}")
        st.write(f"Edge: {ev(sim_a, back_odds_a):.2%}")
        stake = kelly(sim_a, back_odds_a, bankroll, kf)
        if stake >= 2:
            pnl_log.append({"Player": player_a, "Type": "BACK", "Stake": stake, "Prob": sim_a, "Odds": back_odds_a})
            st.success(f"✅ BACK {player_a} with £{stake:.2f}")
        else:
            st.warning("❌ No positive EV.")

    with cb:
        st.write(f"**{player_b} Win %:** {sim_b:.2%}")
        st.write(f"Back Implied: {1/back_odds_b:.2%}")
        st.write(f"Edge: {ev(sim_b, back_odds_b):.2%}")
        stake_b = kelly(sim_b, back_odds_b, bankroll, kf)
        if stake_b >= 2:
            pnl_log.append({"Player": player_b, "Type": "BACK", "Stake": stake_b, "Prob": sim_b, "Odds": back_odds_b})
            st.success(f"✅ BACK {player_b} with £{stake_b:.2f}")
        else:
            st.warning("❌ No positive EV.")

    # Graph
    st.markdown("#### 📈 Probability Distribution")
    fig, ax = plt.subplots()
    ax.hist(np.random.binomial(1, sim_a, sim_points), bins=2, rwidth=0.5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([player_b, player_a])
    ax.set_title("Monte Carlo Match Outcome")
    st.pyplot(fig)

    # P&L Table
    if pnl_log:
        st.markdown("#### 📋 P&L Log")
        df_log = pd.DataFrame(pnl_log)
        df_log["Expected Profit"] = df_log["Stake"] * (df_log["Prob"] * (df_log["Odds"] - 1) - (1 - df_log["Prob"]))
        st.dataframe(df_log)



