import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="ASX Covered Call Screener", layout="wide")

st.title("📈 ASX Mid‑Cap Covered Call Screener")
st.caption("Full‑market scan of ASX tickers using a rules‑based covered‑call system.")

# -----------------------------
# Safe helpers around yfinance
# -----------------------------

def safe_info(ticker):
    try:
        return yf.Ticker(ticker).info
    except:
        return {}

def safe_history(ticker, period="1y"):
    try:
        df = yf.Ticker(ticker).history(period=period)
        return df if df is not None and not df.empty else pd.DataFrame()
    except:
        return pd.DataFrame()

def safe_options(ticker):
    try:
        return yf.Ticker(ticker).options
    except:
        return []

def safe_option_chain(ticker, expiration):
    try:
        return yf.Ticker(ticker).option_chain(expiration)
    except:
        return None

# -----------------------------
# Core metrics
# -----------------------------

def get_put_call_ratio(ticker):
    try:
        tk = yf.Ticker(ticker)
        chain = tk.option_chain()
        puts = chain.puts["volume"].sum()
        calls = chain.calls["volume"].sum()
        return puts / calls if calls > 0 else None
    except:
        return None

def get_best_contract(ticker, min_dte, max_dte):
    today = datetime.now().date()
    dates = safe_options(ticker)
    valid = []

    for d in dates:
        try:
            exp = datetime.strptime(d, "%Y-%m-%d").date()
            dte = (exp - today).days
            if min_dte <= dte <= max_dte:
                valid.append((d, dte))
        except:
            continue

    if not valid:
        return None, None

    midpoint = (min_dte + max_dte) / 2
    return sorted(valid, key=lambda x: abs(x[1] - midpoint))[0]

def get_cc_yield(ticker, expiration):
    chain = safe_option_chain(ticker, expiration)
    if chain is None:
        return None

    calls = chain.calls
    if calls is None or calls.empty:
        return None

    hist = safe_history(ticker, "1d")
    if hist.empty:
        return None

    spot = hist["Close"].iloc[-1]
    calls["diff"] = (calls["strike"] - spot).abs()
    atm = calls.sort_values("diff").iloc[0]

    premium = atm.get("lastPrice", 0)
    if premium is None or premium <= 0 or spot <= 0:
        return None

    return premium / spot

def get_iv_rank(ticker):
    hist = safe_history(ticker, "1y")
    if hist.empty or "Close" not in hist:
        return None

    returns = hist["Close"].pct_change().dropna()
    if returns.empty:
        return None

    iv = returns.std() * (252 ** 0.5)

    rolling = returns.rolling(20).std().dropna()
    if rolling.empty:
        return None

    iv_min = rolling.min() * (252 ** 0.5)
    iv_max = rolling.max() * (252 ** 0.5)

    if iv_max - iv_min == 0:
        return None

    return (iv - iv_min) / (iv_max - iv_min) * 100

# -----------------------------
# Screener logic
# -----------------------------

def screen_ticker(ticker, min_cap, max_cap, min_pcr, max_pcr, min_dte, max_dte, min_ivr, min_cc_yield):
    info = safe_info(ticker)
    mcap = info.get("marketCap", None)

    if mcap is None or not (min_cap <= mcap <= max_cap):
        return None

    pcr = get_put_call_ratio(ticker)
    if pcr is None or not (min_pcr <= pcr <= max_pcr):
        return None

    expiration, dte = get_best_contract(ticker, min_dte, max_dte)
    if expiration is None:
        return None

    cc_yield = get_cc_yield(ticker, expiration)
    if cc_yield is None or cc_yield < min_cc_yield:
        return None

    ivr = get_iv_rank(ticker)
    if ivr is None or ivr < min_ivr:
        return None

    return {
        "Ticker": ticker,
        "MarketCap($B)": round(mcap / 1e9, 2),
        "Put/Call": round(pcr, 2),
        "DTE": dte,
        "Expiration": expiration,
        "CC_Yield_%": round(cc_yield * 100, 2),
        "IV_Rank": round(ivr, 2),
    }

# -----------------------------
# Load ASX universe
# -----------------------------

@st.cache_data
def load_asx_universe():
    path = Path("asx_tickers.csv")
    if not path.exists():
        return []

    df = pd.read_csv(path)
    if "ticker" not in df.columns:
        return []

    # yfinance ASX tickers usually use ".AX" suffix
    return [f"{t.strip().upper()}.AX" for t in df["ticker"] if isinstance(t, str) and t.strip()]

# -----------------------------
# Sidebar filters
# -----------------------------

with st.sidebar:
    st.header("Filters")

    min_cap = st.number_input("Min Market Cap ($B)", 0.1, 100.0, 2.0) * 1e9
    max_cap = st.number_input("Max Market Cap ($B)", 0.1, 500.0, 10.0) * 1e9

    min_pcr = st.number_input("Min Put/Call Ratio", 0.0, 5.0, 0.20)
    max_pcr = st.number_input("Max Put/Call Ratio", 0.0, 5.0, 0.70)

    min_dte = st.number_input("Min DTE", 1, 365, 21)
    max_dte = st.number_input("Max DTE", 1, 365, 36)

    min_ivr = st.number_input("Min IV Rank", 0.0, 100.0, 30.0)
    min_cc_yield = st.number_input("Min Monthly CC Yield (%)", 0.0, 100.0, 12.0) / 100

st.subheader("Universe: ASX full market (from asx_tickers.csv)")

tickers = load_asx_universe()

if not tickers:
    st.error("No ASX universe found. Add 'asx_tickers.csv' with a 'ticker' column to the repo.")
else:
    st.write(f"Loaded **{len(tickers)}** ASX tickers from asx_tickers.csv")

    if st.button("Run Full ASX Scan"):
        results = []
        progress = st.progress(0)

        for i, t in enumerate(tickers):
            progress.progress((i + 1) / len(tickers))
            data = screen_ticker(t, min_cap, max_cap, min_pcr, max_pcr, min_dte, max_dte, min_ivr, min_cc_yield)
            if data:
                results.append(data)

        if results:
            df = pd.DataFrame(results).sort_values("CC_Yield_%", ascending=False)
            st.success(f"Found {len(df)} ASX stocks that match all rules.")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download results as CSV", csv, "asx_covered_call_screen.csv", "text/csv")
        else:
            st.warning("No ASX tickers passed all filters. Loosen thresholds or review your universe file.")
