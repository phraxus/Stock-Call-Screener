import streamlit as st
st.write("App loaded")
import yfinance as yf
import pandas as pd
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------
MIN_CAP = 2e9
MAX_CAP = 10e9

MIN_PCR = 0.20
MAX_PCR = 0.70

MIN_DTE = 21
MAX_DTE = 36

MIN_IVR = 30
MIN_CC_YIELD = 0.12   # 12%

# -----------------------------
# Helper functions
# -----------------------------

def get_put_call_ratio(ticker):
    """Pulls put/call ratio from yfinance (proxy via options volume)."""
    try:
        tk = yf.Ticker(ticker)
        opt = tk.option_chain()
        puts = opt.puts['volume'].sum()
        calls = opt.calls['volume'].sum()
        if calls == 0:
            return None
        return puts / calls
    except:
        return None


def get_best_contract(ticker):
    """Finds the nearest expiration between 21–36 DTE."""
    tk = yf.Ticker(ticker)
    today = datetime.now().date()

    valid_dates = []
    for d in tk.options:
        exp = datetime.strptime(d, "%Y-%m-%d").date()
        dte = (exp - today).days
        if MIN_DTE <= dte <= MAX_DTE:
            valid_dates.append((d, dte))

    if not valid_dates:
        return None, None

    # pick the closest to 30 days
    best = sorted(valid_dates, key=lambda x: abs(x[1] - 30))[0]
    return best[0], best[1]


def get_cc_yield(ticker, expiration):
    """Computes covered-call yield using ATM call premium."""
    tk = yf.Ticker(ticker)
    opt = tk.option_chain(expiration)
    calls = opt.calls

    # ATM call
    spot = tk.history(period="1d")['Close'].iloc[-1]
    calls['diff'] = abs(calls['strike'] - spot)
    atm = calls.sort_values('diff').iloc[0]

    premium = atm['lastPrice']
    if premium <= 0:
        return None

    # Monthly yield approximation
    return premium / spot


def get_iv_rank(ticker):
    """Proxy IV Rank using 1-year historical IV range."""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="1y")
        if 'Close' not in hist:
            return None

        # Use price volatility as IV proxy
        returns = hist['Close'].pct_change().dropna()
        iv = returns.std() * (252 ** 0.5)

        # Fake IV rank: compare to 1-year min/max
        iv_min = returns.rolling(20).std().min() * (252 ** 0.5)
        iv_max = returns.rolling(20).std().max() * (252 ** 0.5)

        if iv_max - iv_min == 0:
            return None

        ivr = (iv - iv_min) / (iv_max - iv_min) * 100
        return ivr
    except:
        return None


# -----------------------------
# MAIN SCREENER
# -----------------------------

def screen_ticker(ticker):
    tk = yf.Ticker(ticker)
    info = tk.info

    # Market cap filter
    mcap = info.get("marketCap", 0)
    if not (MIN_CAP <= mcap <= MAX_CAP):
        return None

    # Put/Call Ratio
    pcr = get_put_call_ratio(ticker)
    if pcr is None or not (MIN_PCR <= pcr <= MAX_PCR):
        return None

    # Expiration window
    expiration, dte = get_best_contract(ticker)
    if expiration is None:
        return None

    # Covered-call yield
    cc_yield = get_cc_yield(ticker, expiration)
    if cc_yield is None or cc_yield < MIN_CC_YIELD:
        return None

    # IV Rank
    ivr = get_iv_rank(ticker)
    if ivr is None or ivr < MIN_IVR:
        return None

    return {
        "Ticker": ticker,
        "MarketCap": mcap,
        "PCR": round(pcr, 2),
        "DTE": dte,
        "Expiration": expiration,
        "CC_Yield": round(cc_yield * 100, 2),
        "IV_Rank": round(ivr, 2)
    }


# -----------------------------
# RUN SCREENER ON WATCHLIST
# -----------------------------

watchlist = [
    "AAPL", "MSFT", "AMD", "MU", "FSLR", "RUN", "ENPH",
    "DKNG", "RBLX", "TTD", "NET", "PLTR", "SQ", "ROKU"
]

results = []

for t in watchlist:
    r = screen_ticker(t)
    if r:
        results.append(r)

df = pd.DataFrame(results)
print(df)
