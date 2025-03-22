# Streamlit App: Doordash Float Strategy + Alpaca Integration

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import alpaca_trade_api as tradeapi

# ---- Alpaca API (Paper) ----
ALPACA_API_KEY = "PK0LP1D1PCK7D9G5KMOJ"
ALPACA_SECRET_KEY = "YuLfuP2H1hYRWOrfj6fhxzsVjff22y4BdZ6iTZ1G"
BASE_URL = "https://paper-api.alpaca.markets"

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL)

# ---- Sector Logic ----
SECTOR_ETF_MAP = {
    "groceries": "XLP",
    "fast_food": "XLY",
    "pharmacy": "XLV"
}

def simulate_order_type():
    return random.choices(
        population=list(SECTOR_ETF_MAP.keys()),
        weights=[0.5, 0.3, 0.2],
        k=1
    )[0]

def get_sector_volatility(etf, days):
    try:
        data = yf.download(etf, period="1y")
        data["Returns"] = data["Adj Close"].pct_change()
        return data["Returns"].rolling(window=7).std().fillna(0).tolist()[:days]
    except:
        return [0.01] * days

def get_bond_yields(days):
    np.random.seed(42)
    return (
        0.05 + np.random.normal(0, 0.002, days),
        0.055 + np.random.normal(0, 0.002, days),
        0.057 + np.random.normal(0, 0.002, days),
    )

def submit_trade(symbol="SPY", qty=1, side="buy"):
    try:
        order = api.submit_order(symbol=symbol, qty=qty, side=side, type="market", time_in_force="gtc")
        return f"✅ {side.capitalize()} {qty} shares of {symbol}"
    except Exception as e:
        return f"⚠️ Trade failed: {e}"

# ---- Streamlit UI ----
st.set_page_config(page_title="Doordash Float Strategy", layout="wide")
st.title("📈 Doordash Float Arbitrage Dashboard + Live Alpaca Trading")

days = st.slider("Simulation Days", 7, 90, 30)
daily_spend = st.number_input("Avg Daily Spend ($)", 10.0, 300.0, 85.0, step=1.0)
trade_threshold = st.slider("Trade Trigger: Option Income ≥", 0.0, 10.0, 3.5, step=0.5)

run_sim = st.button("🚀 Run Strategy")

if run_sim:
    start_date = datetime.today()
    active_floats = []
    results = []
    trades = []
    profit = 0
    order_type = simulate_order_type()
    etf = SECTOR_ETF_MAP[order_type]
    vols = get_sector_volatility(etf, days)
    one_mo, three_mo, one_yr = get_bond_yields(days)
    offsets = [0, 14, 28, 42]

    for i in range(days):
        today = start_date + timedelta(days=i)
        new_float = round(daily_spend * random.uniform(0.85, 1.15), 2)
        active_floats.append({"start": today, "end": today + timedelta(days=42), "amt": new_float})

        day_profit, total_float = 0, 0
        for f in active_floats:
            if f["start"] <= today < f["end"]:
                total_float += f["amt"]
                bond_yield = max(one_mo[i], three_mo[i], one_yr[i])
                cash_yield = 0.0375
                bond_part = f["amt"] * 0.75
                cash_part = f["amt"] * 0.25
                day_profit += bond_part * (bond_yield / 365) + cash_part * (cash_yield / 365)

        vol_mult = 1 + vols[i] * 100
        option_income = ((total_float / 1000) * (7 / 7)) * vol_mult
        day_profit += option_income
        profit += day_profit

        if option_income >= trade_threshold:
            trade_result = submit_trade()
            trades.append((today.strftime("%Y-%m-%d"), trade_result))

        results.append({
            "Date": today.strftime("%Y-%m-%d"),
            "New Float ($)": new_float,
            "Active Float ($)": round(total_float, 2),
            "Daily Profit ($)": round(day_profit, 2),
            "Cumulative Profit ($)": round(profit, 2),
            "Option Income ($)": round(option_income, 2),
            "Vol Multiplier": round(vol_mult, 2),
            "1M Yld": round(one_mo[i]*100, 2),
            "3M Yld": round(three_mo[i]*100, 2),
            "1Y Yld": round(one_yr[i]*100, 2)
        })

    df = pd.DataFrame(results)

    st.subheader("📊 Cumulative Profit")
    st.line_chart(df.set_index("Date")["Cumulative Profit ($)"])

    st.subheader("📈 Option Income")
    st.line_chart(df.set_index("Date")["Option Income ($)"])

    st.subheader("📉 Yield Curve")
    yield_plot = df[["Date", "1M Yld", "3M Yld", "1Y Yld"]].set_index("Date")
    st.line_chart(yield_plot)

    st.subheader("📋 Daily Summary")
    st.dataframe(df)

    st.subheader("🧾 Trade Log")
    for t in trades:
        st.write(f"{t[0]} - {t[1]}")