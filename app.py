import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import pytz
import time
import os
import re
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pyotp

# Safe Optional Imports
try:
    from SmartApi import SmartConnect
    SMARTAPI_AVAILABLE = True
except ImportError:
    SMARTAPI_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# ==============================================================================
# 1. PAGE CONFIGURATION & INSTITUTIONAL DARK UI CSS
# ==============================================================================
st.set_page_config(
    page_title="MCX Institutional Intelligence Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

IST = pytz.timezone("Asia/Kolkata")
LOCAL_LOCK_FILE = Path(".angel_creds_cache.json")

st.markdown("""
<style>
    .block-container { padding-top: 0.8rem; padding-bottom: 1.5rem; max-width: 98%; }
    
    /* Signal Banners */
    .banner-wait {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-left: 7px solid #f59e0b;
        padding: 18px 20px;
        border-radius: 10px;
        color: #f8fafc;
        margin-bottom: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }
    .banner-buy {
        background: linear-gradient(135deg, #064e3b 0%, #022c22 100%);
        border: 1px solid #059669;
        border-left: 7px solid #10b981;
        padding: 18px 20px;
        border-radius: 10px;
        color: #ecfdf5;
        margin-bottom: 14px;
        box-shadow: 0 4px 15px rgba(16,185,129,0.2);
    }
    .banner-sell {
        background: linear-gradient(135deg, #7f1d1d 0%, #450a0a 100%);
        border: 1px solid #dc2626;
        border-left: 7px solid #ef4444;
        padding: 18px 20px;
        border-radius: 10px;
        color: #fef2f2;
        margin-bottom: 14px;
        box-shadow: 0 4px 15px rgba(239,68,68,0.2);
    }
    
    /* Badges & Pills */
    .ist-clock {
        background-color: #0f172a;
        border: 1px solid #38bdf8;
        color: #38bdf8;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.92rem;
        display: inline-block;
    }
    .level-box {
        background-color: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 8px;
        font-size: 0.88rem;
    }
    .check-pass { color: #34d399; font-weight: 600; }
    .check-wait { color: #fbbf24; font-weight: 500; }
    .check-fail { color: #f87171; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 2. CONTRACT SPECIFICATIONS & CONSTANTS
# ==============================================================================
MCX_SPECS = {
    "Natural Gas": {
        "mini_symbol": "NATGASMINI",
        "mega_symbol": "NATURALGAS",
        "yf_ticker": "NG=F",
        "mini_lot": 250,
        "mega_lot": 1250,
        "strike_step": 5,
        "unit": "MMBtu"
    },
    "Crude Oil": {
        "mini_symbol": "CRUDEOILM",
        "mega_symbol": "CRUDEOIL",
        "yf_ticker": "CL=F",
        "mini_lot": 10,
        "mega_lot": 100,
        "strike_step": 50,
        "unit": "BBL"
    }
}


# ==============================================================================
# 3. UNIVERSAL CREDENTIAL PARSER (SUPPORTS TOML, JSON, SECRETS, ENV & LOCK FILE)
# ==============================================================================
def parse_raw_creds_string(raw_str: str) -> dict:
    if not raw_str:
        return {}
    raw_str = raw_str.strip()
    try:
        data = json.loads(raw_str)
        if isinstance(data, dict):
            return data.get("angel_one", data)
    except Exception:
        pass

    extracted = {}
    for key in ["api_key", "client_id", "pin", "totp_secret"]:
        match = re.search(rf'{key}\s*=\s*["\']?([^"\'\n\r]+)["\']?', raw_str, re.IGNORECASE)
        if match:
            extracted[key] = match.group(1).strip()
    return extracted


def load_angel_credentials() -> dict:
    creds = {}
    # 1. Streamlit Secrets
    try:
        if "angel_one" in st.secrets:
            creds = dict(st.secrets["angel_one"])
        elif "ANGEL_ONE_CREDS" in st.secrets:
            creds = parse_raw_creds_string(str(st.secrets["ANGEL_ONE_CREDS"]))
        elif "api_key" in st.secrets:
            creds = {
                "api_key": st.secrets["api_key"],
                "client_id": st.secrets["client_id"],
                "pin": st.secrets["pin"],
                "totp_secret": st.secrets["totp_secret"],
            }
    except Exception:
        pass

    # 2. OS Environment Variable (GitHub Actions / Codespaces)
    if not creds.get("api_key") and "ANGEL_ONE_CREDS" in os.environ:
        creds = parse_raw_creds_string(os.environ["ANGEL_ONE_CREDS"])

    # 3. Local Persistent Server Cache
    if not creds.get("api_key") and LOCAL_LOCK_FILE.exists():
        try:
            creds = json.loads(LOCAL_LOCK_FILE.read_text())
        except Exception:
            pass

    return creds


# ==============================================================================
# 4. ULTRA-FAST ANGEL ONE SMARTAPI ENGINE (CACHED SESSION & TOKENS)
# ==============================================================================
@st.cache_resource(ttl=3600 * 6, show_spinner=False)
def get_angel_connection(api_key: str, client_id: str, pin: str, totp_secret: str):
    if not SMARTAPI_AVAILABLE:
        return None, "smartapi-python not installed"
    try:
        clean_totp = re.sub(r"\s+", "", totp_secret)
        totp_code = pyotp.TOTP(clean_totp).now()
        obj = SmartConnect(api_key=api_key.strip())
        sess = obj.generateSession(client_id.strip(), str(pin).strip(), totp_code)
        if sess and sess.get("status"):
            return obj, "Connected"
        msg = sess.get("message", "Login failed") if sess else "Empty response"
        return None, f"Angel Error: {msg}"
    except Exception as e:
        return None, f"Auth Exception: {str(e)}"


@st.cache_data(ttl=3600 * 8, show_spinner=False)
def resolve_mcx_futures_contract(_smart_api, symbol_prefix: str):
    """Finds active nearest-month MCX Futures contract in <0.2s via searchScrip."""
    if _smart_api is None:
        return None
    try:
        res = _smart_api.searchScrip(exchange="MCX", searchscrip=symbol_prefix)
        if res and res.get("status") and res.get("data"):
            candidates = [
                item for item in res["data"]
                if item.get("tradingsymbol", "").startswith(symbol_prefix)
                and item.get("tradingsymbol", "").endswith("FUT")
            ]
            if candidates:
                return candidates[0]
            return res["data"][0]
    except Exception:
        pass
    return None


def fetch_angel_market_bundle(smart_api, primary_sym: str, fallback_sym: str, angel_tf: str):
    """Fetches full quote (LTP, Open, High, Low, Close) + Historical Intraday Candles."""
    contract = resolve_mcx_futures_contract(smart_api, primary_sym)
    if not contract and fallback_sym:
        contract = resolve_mcx_futures_contract(smart_api, fallback_sym)

    if not contract:
        return None, {}, primary_sym

    token = contract["symboltoken"]
    tradingsymbol = contract["tradingsymbol"]
    quote_meta = {"ltp": None, "open": None, "high": None, "low": None, "close": None}

    # 1. Fetch Live Quote / LTP
    try:
        q_res = smart_api.ltpData("MCX", tradingsymbol, token)
        if q_res and q_res.get("status") and q_res.get("data"):
            d = q_res["data"]
            quote_meta["ltp"] = float(d.get("ltp", 0))
            quote_meta["open"] = float(d.get("open", quote_meta["ltp"]))
            quote_meta["high"] = float(d.get("high", quote_meta["ltp"]))
            quote_meta["low"] = float(d.get("low", quote_meta["ltp"]))
            quote_meta["close"] = float(d.get("close", quote_meta["ltp"]))
    except Exception:
        pass

    # 2. Fetch Intraday Candles
    now_ist = datetime.now(IST)
    from_str = (now_ist - timedelta(days=6)).strftime("%Y-%m-%d 09:00")
    to_str = now_ist.strftime("%Y-%m-%d %H:%M")

    df = None
    try:
        params = {
            "exchange": "MCX",
            "symboltoken": token,
            "interval": angel_tf,
            "fromdate": from_str,
            "todate": to_str
        }
        c_res = smart_api.getCandleData(params)
        if c_res and c_res.get("status") and c_res.get("data"):
            df = pd.DataFrame(
                c_res["data"],
                columns=["timestamp", "Open", "High", "Low", "Close", "Volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert(IST)
            for c in ["Open", "High", "Low", "Close", "Volume"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            df = df.sort_values("timestamp").reset_index(drop=True)

            if not df.empty:
                if quote_meta["ltp"] is None or quote_meta["ltp"] <= 0:
                    quote_meta["ltp"] = float(df["Close"].iloc[-1])
                else:
                    df.loc[df.index[-1], "Close"] = quote_meta["ltp"]
                    if quote_meta["ltp"] > df.loc[df.index[-1], "High"]:
                        df.loc[df.index[-1], "High"] = quote_meta["ltp"]
                    if quote_meta["ltp"] < df.loc[df.index[-1], "Low"]:
                        df.loc[df.index[-1], "Low"] = quote_meta["ltp"]
    except Exception:
        pass

    return df, quote_meta, tradingsymbol


@st.cache_data(ttl=45, show_spinner=False)
def fetch_global_and_fallback_candles(yf_ticker: str, target_ltp: float = None, yf_tf: str = "15m"):
    """Fetches global NYMEX price change + calibrated fallback candles if Angel historical throttles."""
    if not YFINANCE_AVAILABLE:
        return None, {}
    try:
        tk = yf.Ticker(yf_ticker)
        hist = tk.history(period="5d", interval=yf_tf)
        if hist is None or hist.empty:
            return None, {}
        hist = hist.reset_index()
        t_col = "Datetime" if "Datetime" in hist.columns else "Date"
        hist["timestamp"] = pd.to_datetime(hist[t_col])
        if hist["timestamp"].dt.tz is None:
            hist["timestamp"] = hist["timestamp"].dt.tz_localize("UTC").dt.tz_convert(IST)
        else:
            hist["timestamp"] = hist["timestamp"].dt.tz_convert(IST)

        df = hist[["timestamp", "Open", "High", "Low", "Close", "Volume"]].copy()
        global_last = float(df["Close"].iloc[-1])
        global_prev = float(df["Close"].iloc[-2]) if len(df) > 1 else global_last
        global_chg_pct = round(((global_last - global_prev) / global_prev) * 100, 2) if global_prev else 0.0

        if target_ltp and target_ltp > 0:
            scale = target_ltp / global_last
            for c in ["Open", "High", "Low", "Close"]:
                df[c] = (df[c] * scale).round(2)
        elif yf_ticker in ["NG=F", "CL=F"]:
            for c in ["Open", "High", "Low", "Close"]:
                df[c] = (df[c] * 86.5).round(2)

        meta = {
            "global_price": round(global_last, 3),
            "global_chg_pct": global_chg_pct
        }
        return df.tail(160).reset_index(drop=True), meta
    except Exception:
        return None, {}


# ==============================================================================
# 5. INSTITUTIONAL INDICATOR SUITE (SUPERTREND, VWAP, CPR, EMA, ADX, MACD, RSI)
# ==============================================================================
def compute_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    hl2 = (df["High"] + df["Low"]) / 2.0
    atr = df["ATR"]
    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)

    final_upper = upperband.copy()
    final_lower = lowerband.copy()
    st_dir = np.ones(len(df), dtype=int)
    st_line = np.zeros(len(df), dtype=float)

    close_arr = df["Close"].values
    up_arr = upperband.values
    low_arr = lowerband.values
    f_up = final_upper.values
    f_low = final_lower.values

    for i in range(1, len(df)):
        if up_arr[i] < f_up[i - 1] or close_arr[i - 1] > f_up[i - 1]:
            f_up[i] = up_arr[i]
        else:
            f_up[i] = f_up[i - 1]

        if low_arr[i] > f_low[i - 1] or close_arr[i - 1] < f_low[i - 1]:
            f_low[i] = low_arr[i]
        else:
            f_low[i] = f_low[i - 1]

        if st_dir[i - 1] == -1 and close_arr[i] > f_up[i - 1]:
            st_dir[i] = 1
        elif st_dir[i - 1] == 1 and close_arr[i] < f_low[i - 1]:
            st_dir[i] = -1
        else:
            st_dir[i] = st_dir[i - 1]

        st_line[i] = f_low[i] if st_dir[i] == 1 else f_up[i]

    df["Supertrend"] = st_line
    df["ST_Dir"] = st_dir
    return df


def compute_pivots_and_cpr(df: pd.DataFrame):
    """Calculates Floor Pivots (P, R1, R2, S1, S2) & Central Pivot Range (CPR) from prior session."""
    df["date"] = df["timestamp"].dt.date
    unique_dates = sorted(df["date"].unique())
    if len(unique_dates) >= 2:
        prev_day_df = df[df["date"] == unique_dates[-2]]
    else:
        prev_day_df = df.iloc[:max(10, len(df) // 2)]

    h = float(prev_day_df["High"].max())
    l = float(prev_day_df["Low"].min())
    c = float(prev_day_df["Close"].iloc[-1])

    pivot = (h + l + c) / 3.0
    bc = (h + l) / 2.0
    tc = (pivot - bc) + pivot
    r1 = (2 * pivot) - l
    s1 = (2 * pivot) - h
    r2 = pivot + (h - l)
    s2 = pivot - (h - l)

    return {
        "P": round(pivot, 2),
        "TC": round(max(tc, bc), 2),
        "BC": round(min(tc, bc), 2),
        "R1": round(r1, 2),
        "R2": round(r2, 2),
        "S1": round(s1, 2),
        "S2": round(s2, 2)
    }


# ==============================================================================
# 6. STRICT EVENT-BASED SETUP ENGINE (ZERO FAKE SIGNALS + EXACT TIMESTAMPS)
# ==============================================================================
def analyze_market_strictly(df: pd.DataFrame, commodity_name: str, sensitivity_mode: str = "Strict Institutional"):
    if df is None or len(df) < 35:
        return None

    df = df.copy().reset_index(drop=True)

    # 1. Moving Averages (EMA 9, 21, 50)
    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA21"] = df["Close"].ewm(span=21, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    # 2. Intraday Session VWAP
    df["date"] = df["timestamp"].dt.date
    df["typ"] = (df["High"] + df["Low"] + df["Close"]) / 3.0
    df["vol_clean"] = df["Volume"].replace(0, 1)
    df["tp_v"] = df["typ"] * df["vol_clean"]
    df["VWAP"] = df.groupby("date")["tp_v"].cumsum() / df.groupby("date")["vol_clean"].cumsum()

    # 3. ATR (14)
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1 / 14, adjust=False).mean().bfill()

    # 4. Supertrend (10, 3.0)
    df = compute_supertrend(df, period=10, multiplier=3.0)

    # 5. RSI (14)
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_g = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_l = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = avg_g / avg_l.replace(0, np.nan)
    df["RSI"] = (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)

    # 6. MACD (12, 26, 9)
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    # 7. ADX (14) Trend Strength
    up = df["High"].diff()
    dn = -df["Low"].diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr_s = tr.ewm(alpha=1 / 14, adjust=False).mean().replace(0, np.nan)
    pdi = 100 * (pd.Series(pdm, index=df.index).ewm(alpha=1 / 14, adjust=False).mean() / tr_s)
    mdi = 100 * (pd.Series(mdm, index=df.index).ewm(alpha=1 / 14, adjust=False).mean() / tr_s)
    dx = 100 * ((pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan))
    df["ADX"] = dx.ewm(alpha=1 / 14, adjust=False).mean().fillna(15.0)

    # 8. Structure Breakout (3-Candle High/Low) & Volume Activity
    df["Prev3_High"] = df["High"].shift(1).rolling(3).max()
    df["Prev3_Low"] = df["Low"].shift(1).rolling(3).min()
    df["Vol_SMA20"] = df["vol_clean"].rolling(20, min_periods=5).mean().bfill()
    df["Vol_Ratio"] = (df["vol_clean"] / df["Vol_SMA20"]).round(2)

    adx_min = 20.0 if "Strict" in sensitivity_mode else 17.5
    rsi_buy_min = 56.0 if "Strict" in sensitivity_mode else 54.0
    rsi_sell_max = 44.0 if "Strict" in sensitivity_mode else 46.0

    bull_aligned = (
        (df["ST_Dir"] == 1) &
        (df["EMA9"] > df["EMA21"]) &
        (df["Close"] > df["VWAP"]) &
        (df["RSI"] >= rsi_buy_min) & (df["RSI"] <= 73.0) &
        (df["MACD"] > df["MACD_Signal"]) &
        (df["ADX"] >= adx_min) &
        (df["Close"] > df["Prev3_High"])
    )

    bear_aligned = (
        (df["ST_Dir"] == -1) &
        (df["EMA9"] < df["EMA21"]) &
        (df["Close"] < df["VWAP"]) &
        (df["RSI"] <= rsi_sell_max) & (df["RSI"] >= 27.0) &
        (df["MACD"] < df["MACD_Signal"]) &
        (df["ADX"] >= adx_min) &
        (df["Close"] < df["Prev3_Low"])
    )

    # EVENT-BASED TRIGGER: Only fire on the FIRST breakout candle
    df["Trigger"] = "NONE"
    prev_bull = bull_aligned.shift(1, fill_value=False)
    prev_bear = bear_aligned.shift(1, fill_value=False)

    df.loc[bull_aligned & (~prev_bull), "Trigger"] = "BUY"
    df.loc[bear_aligned & (~prev_bear), "Trigger"] = "SELL"

    signal_log = []
    for idx, row in df[df["Trigger"].isin(["BUY", "SELL"])].iterrows():
        sig_type = row["Trigger"]
        trig_price = round(float(row["Close"]), 2)
        atr_v = max(float(row["ATR"]), trig_price * 0.0035)
        risk_pts = round(1.5 * atr_v, 2)

        if sig_type == "BUY":
            sl_p = round(trig_price - risk_pts, 2)
            t1_p = round(trig_price + (risk_pts * 1.8), 2)
            t2_p = round(trig_price + (risk_pts * 2.8), 2)
        else:
            sl_p = round(trig_price + risk_pts, 2)
            t1_p = round(trig_price - (risk_pts * 1.8), 2)
            t2_p = round(trig_price - (risk_pts * 2.8), 2)

        future_slice = df.iloc[idx + 1:]
        status_label = "ACTIVE NOW"
        if not future_slice.empty:
            for _, f_row in future_slice.iterrows():
                if sig_type == "BUY":
                    if f_row["Low"] <= sl_p:
                        status_label = "SL HIT 🛑"
                        break
                    if f_row["High"] >= t1_p:
                        status_label = "TARGET HIT ✅"
                        break
                else:
                    if f_row["High"] >= sl_p:
                        status_label = "SL HIT 🛑"
                        break
                    if f_row["Low"] <= t1_p:
                        status_label = "TARGET HIT ✅"
                        break
            if status_label == "ACTIVE NOW" and len(future_slice) > 2:
                status_label = "ENTRY WINDOW CLOSED ⌛"

        signal_log.append({
            "idx": idx,
            "Time (IST)": row["timestamp"].strftime("%d %b, %I:%M %p"),
            "timestamp_dt": row["timestamp"],
            "Signal": sig_type,
            "Trigger Price": trig_price,
            "Stop Loss": sl_p,
            "Target 1": t1_p,
            "Target 2": t2_p,
            "RSI": round(float(row["RSI"]), 1),
            "ADX": round(float(row["ADX"]), 1),
            "Status": status_label,
            "risk_pts": risk_pts
        })

    last = df.iloc[-1]
    current_ltp = round(float(last["Close"]), 2)
    current_atr = max(float(last["ATR"]), current_ltp * 0.0035)

    active_setup = None
    if signal_log:
        latest_sig = signal_log[-1]
        candles_since_trigger = (len(df) - 1) - latest_sig["idx"]
        price_drift = abs(current_ltp - latest_sig["Trigger Price"])

        if (
            candles_since_trigger <= 1
            and latest_sig["Status"] == "ACTIVE NOW"
            and price_drift <= (0.85 * current_atr)
        ):
            active_setup = latest_sig

    # 6-Point Diagnostic Checklist
    checklist = []
    if last["ST_Dir"] == 1:
        checklist.append(("PASS", f"Supertrend (10,3): Bullish Support at ₹{last['Supertrend']:.2f}"))
    else:
        checklist.append(("PASS", f"Supertrend (10,3): Bearish Resistance at ₹{last['Supertrend']:.2f}"))

    if last["EMA9"] > last["EMA21"] and last["Close"] > last["VWAP"]:
        checklist.append(("PASS", f"EMA 9/21 & VWAP: Bullish Alignment (Above VWAP ₹{last['VWAP']:.2f})"))
    elif last["EMA9"] < last["EMA21"] and last["Close"] < last["VWAP"]:
        checklist.append(("PASS", f"EMA 9/21 & VWAP: Bearish Alignment (Below VWAP ₹{last['VWAP']:.2f})"))
    else:
        checklist.append(("WAIT", f"EMA & VWAP Conflict: Price mixed between EMA21 (₹{last['EMA21']:.2f}) & VWAP (₹{last['VWAP']:.2f})"))

    r_val = float(last["RSI"])
    if rsi_buy_min <= r_val <= 73.0:
        checklist.append(("PASS", f"RSI (14) Momentum: Strong Bullish Zone ({r_val:.1f})"))
    elif 27.0 <= r_val <= rsi_sell_max:
        checklist.append(("PASS", f"RSI (14) Momentum: Strong Bearish Zone ({r_val:.1f})"))
    else:
        checklist.append(("WAIT", f"RSI (14) Neutral/ChopZone: {r_val:.1f} (Needs >{rsi_buy_min:.0f} for Buy or <{rsi_sell_max:.0f} for Sell)"))

    if last["MACD"] > last["MACD_Signal"]:
        checklist.append(("PASS", f"MACD Histogram: Positive Momentum (+{last['MACD_Hist']:.2f})"))
    else:
        checklist.append(("PASS", f"MACD Histogram: Negative Momentum ({last['MACD_Hist']:.2f})"))

    adx_v = float(last["ADX"])
    if adx_v >= adx_min:
        checklist.append(("PASS", f"ADX Trend Strength: {adx_v:.1f} (Strong Trending Market)"))
    else:
        checklist.append(("WAIT", f"ADX Trend Strength: {adx_v:.1f} < {adx_min:.0f} (Sideways / Low Momentum Market)"))

    if last["Close"] > last["Prev3_High"]:
        checklist.append(("PASS", f"Breakout Confirmed: Crossed 3-Candle High (₹{last['Prev3_High']:.2f})"))
    elif last["Close"] < last["Prev3_Low"]:
        checklist.append(("PASS", f"Breakdown Confirmed: Crossed 3-Candle Low (₹{last['Prev3_Low']:.2f})"))
    else:
        checklist.append(("WAIT", f"Inside Candle Range: Waiting for Breakout above ₹{last['Prev3_High']:.2f} or below ₹{last['Prev3_Low']:.2f}"))

    pivots = compute_pivots_and_cpr(df)

    return {
        "df": df,
        "ltp": current_ltp,
        "atr": round(current_atr, 2),
        "vwap": round(float(last["VWAP"]), 2),
        "ema9": round(float(last["EMA9"]), 2),
        "ema21": round(float(last["EMA21"]), 2),
        "ema50": round(float(last["EMA50"]), 2),
        "supertrend": round(float(last["Supertrend"]), 2),
        "st_dir": int(last["ST_Dir"]),
        "rsi": round(r_val, 1),
        "adx": round(adx_v, 1),
        "vol_ratio": float(last["Vol_Ratio"]),
        "pivots": pivots,
        "active_setup": active_setup,
        "signal_log": signal_log,
        "checklist": checklist
    }


# ==============================================================================
# 7. OPTION STRIKE & POSITION SIZING HELPER
# ==============================================================================
def get_option_and_lot_recommendation(commodity_name: str, ltp: float, active_setup: dict, capital_risk_inr: float):
    spec = MCX_SPECS[commodity_name]
    step = spec["strike_step"]
    atm_strike = int(round(ltp / step) * step)

    if not active_setup:
        return {
            "status": "WAIT",
            "atm": atm_strike,
            "message": "No Option Trade Suggested Right Now — Wait for Confirmed Setup"
        }

    sig = active_setup["Signal"]
    risk_pts = max(active_setup["risk_pts"], 0.5)
    mini_lot_size = spec["mini_lot"]
    risk_per_mini_lot = round(risk_pts * mini_lot_size, 2)
    rec_mini_lots = max(1, int(capital_risk_inr // max(risk_per_mini_lot, 1)))

    if sig == "BUY":
        opt_type = "CE (Call Option)"
        atm_pick = f"{atm_strike} CE"
        itm_pick = f"{atm_strike - step} CE (Safe ITM)"
    else:
        opt_type = "PE (Put Option)"
        atm_pick = f"{atm_strike} PE"
        itm_pick = f"{atm_strike + step} PE (Safe ITM)"

    return {
        "status": sig,
        "opt_type": opt_type,
        "atm_pick": atm_pick,
        "itm_pick": itm_pick,
        "mini_lot_size": mini_lot_size,
        "risk_per_mini_lot": risk_per_mini_lot,
        "rec_mini_lots": rec_mini_lots
    }


# ==============================================================================
# 8. INTERACTIVE PLOTLY CHART WITH EXACT IST TRIGGER TIMESTAMPS
# ==============================================================================
def render_institutional_chart(analysis: dict, title: str):
    df = analysis["df"].tail(75).copy()

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.78, 0.22]
    )

    # 1. Candlesticks
    fig.add_trace(go.Candlestick(
        x=df["timestamp"],
        open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="MCX Price",
        increasing_line_color="#10b981",
        decreasing_line_color="#ef4444"
    ), row=1, col=1)

    # 2. EMA 9, EMA 21, VWAP & Supertrend
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["EMA9"],
        mode="lines", name="EMA 9",
        line=dict(color="#38bdf8", width=1.4)
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["EMA21"],
        mode="lines", name="EMA 21",
        line=dict(color="#f59e0b", width=1.4)
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["VWAP"],
        mode="lines", name="Session VWAP",
        line=dict(color="#c084fc", width=1.8, dash="dot")
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["Supertrend"],
        mode="lines", name="Supertrend (10,3)",
        line=dict(color="#22d3ee", width=1.3, dash="dash")
    ), row=1, col=1)

    # 3. Exact BUY / SELL Trigger Markers with IST Time Text
    buys = df[df["Trigger"] == "BUY"]
    sells = df[df["Trigger"] == "SELL"]

    if not buys.empty:
        fig.add_trace(go.Scatter(
            x=buys["timestamp"],
            y=buys["Low"] * 0.997,
            mode="markers+text",
            name="BUY Trigger Time",
            text=[f"BUY ({t.strftime('%H:%M')})" for t in buys["timestamp"]],
            textposition="bottom center",
            textfont=dict(color="#34d399", size=11),
            marker=dict(symbol="triangle-up", size=14, color="#10b981", line=dict(width=1.5, color="white"))
        ), row=1, col=1)

    if not sells.empty:
        fig.add_trace(go.Scatter(
            x=sells["timestamp"],
            y=sells["High"] * 1.003,
            mode="markers+text",
            name="SELL Trigger Time",
            text=[f"SELL ({t.strftime('%H:%M')})" for t in sells["timestamp"]],
            textposition="top center",
            textfont=dict(color="#f87171", size=11),
            marker=dict(symbol="triangle-down", size=14, color="#ef4444", line=dict(width=1.5, color="white"))
        ), row=1, col=1)

    # 4. Plot Active Entry, SL & Target Lines if a Confirmed Trade is Live
    act = analysis["active_setup"]
    if act:
        trig_val = act["Trigger Price"]
        sl_val = act["Stop Loss"]
        t1_val = act["Target 1"]
        fig.add_hline(y=trig_val, line_dash="solid", line_color="#38bdf8",
                      annotation_text=f"Entry ₹{trig_val}", row=1, col=1)
        fig.add_hline(y=sl_val, line_dash="dot", line_color="#ef4444",
                      annotation_text=f"SL ₹{sl_val}", row=1, col=1)
        fig.add_hline(y=t1_val, line_dash="dot", line_color="#10b981",
                      annotation_text=f"T1 ₹{t1_val}", row=1, col=1)

    # 5. RSI Subplot
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["RSI"],
        mode="lines", name="RSI (14)",
        line=dict(color="#a78bfa", width=1.6)
    ), row=2, col=1)
    fig.add_hline(y=56, line_dash="dot", line_color="#10b981", row=2, col=1)
    fig.add_hline(y=44, line_dash="dot", line_color="#ef4444", row=2, col=1)

    fig.update_layout(
        title=dict(text=f"{title} — Institutional Chart (IST Timestamps)", font=dict(size=15)),
        template="plotly_dark",
        height=490,
        margin=dict(l=10, r=10, t=38, b=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis2=dict(title="Time (IST)", tickformat="%H:%M\n%d %b"),
        yaxis=dict(title="Price (₹)"),
        yaxis2=dict(title="RSI", range=[20, 85])
    )
    st.plotly_chart(fig, use_container_width=True)


# ==============================================================================
# 9. SIDEBAR CONTROLS & CREDENTIAL MANAGER
# ==============================================================================
with st.sidebar:
    st.markdown("## ⚙️ Terminal Controls")
    timeframe_choice = st.selectbox(
        "⏱️ Chart Timeframe",
        ["15 Minute (Intraday Pro)", "5 Minute (Fast Scalping)", "30 Minute (Swing)"],
        index=0
    )
    sensitivity_choice = st.radio(
        "🎯 Signal Filter Strictness",
        ["Strict Institutional (Zero Noise)", "Standard Intraday"],
        index=0
    )
    risk_per_trade_inr = st.number_input(
        "💰 Max Risk Per Trade (₹)",
        min_value=500, max_value=100000, value=1500, step=250
    )
    auto_refresh = st.toggle("🔄 Auto-Refresh Every 30s", value=False)
    st.divider()
    st.caption("📁 Multi-page navigation (OPEC & EIA Reports) is active above in the sidebar.")

if "15" in timeframe_choice:
    angel_tf, yf_tf = "FIFTEEN_MINUTE", "15m"
elif "5" in timeframe_choice:
    angel_tf, yf_tf = "FIVE_MINUTE", "5m"
else:
    angel_tf, yf_tf = "THIRTY_MINUTE", "30m"

# Load Credentials
creds = load_angel_credentials()
api_key = creds.get("api_key", "")
client_id = creds.get("client_id", "")
pin = creds.get("pin", "")
totp_secret = creds.get("totp_secret", "")

now_ist = datetime.now(IST)
now_ist_str = now_ist.strftime("%d %b %Y | %I:%M:%S %p IST")

# Top Header
hdr1, hdr2, hdr3 = st.columns([2.6, 1.4, 0.8])
with hdr1:
    st.markdown("## ⚡ MCX Live Institutional Terminal (`NATGASMINI` & `CRUDEOILM`)")
with hdr2:
    st.markdown(f"<div style='padding-top:10px;'><span class='ist-clock'>🕒 {now_ist_str}</span></div>", unsafe_allow_html=True)
with hdr3:
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()

# One-Time Locker if Streamlit Cloud hasn't received TOML keys yet
if not (api_key and client_id and pin and totp_secret):
    with st.expander("🔐 One-Time Angel One Secret Activation (Click to Lock Credentials)", expanded=True):
        st.info("GitHub Actions Secrets sirf workflows me rehte hain. Apna TOML block yahan ek baar paste kar dein—yeh server par save ho jayega.")
        raw_input = st.text_area(
            "Paste [angel_one] credentials:",
            height=130,
            placeholder='[angel_one]\napi_key = "..."\nclient_id = "..."\npin = "..."\ntotp_secret = "..."'
        )
        if st.button("🔒 Lock & Connect"):
            parsed = parse_raw_creds_string(raw_input)
            if parsed.get("api_key") and parsed.get("client_id"):
                LOCAL_LOCK_FILE.write_text(json.dumps(parsed))
                st.success("Credentials locked! Re-initializing...")
                st.rerun()
            else:
                st.error("Invalid format. Charo fields check karein.")

smart_api = None
conn_status = "Not Connected"
if api_key and client_id and pin and totp_secret:
    smart_api, conn_status = get_angel_connection(api_key, client_id, pin, totp_secret)

if smart_api:
    st.success(f"🟢 **Angel One SmartAPI Live Connected** (Account: `{client_id}`) — Strict Timestamped Setup Engine Active")
else:
    st.warning(f"⚠️ **Angel Feed Status:** `{conn_status}` — Running on Calibrated Backup Feed until connected.")


# ==============================================================================
# 10. PARALLEL HIGH-SPEED MARKET DATA LOADER (<1.5 SECONDS)
# ==============================================================================
def load_complete_commodity(comm_name: str):
    spec = MCX_SPECS[comm_name]
    df, quote_meta, contract_symbol = None, {}, spec["mini_symbol"]

    if smart_api:
        df, quote_meta, contract_symbol = fetch_angel_market_bundle(
            smart_api, spec["mini_symbol"], spec["mega_symbol"], angel_tf
        )

    fallback_df, global_meta = fetch_global_and_fallback_candles(
        spec["yf_ticker"], target_ltp=quote_meta.get("ltp"), yf_tf=yf_tf
    )

    if df is None or len(df) < 35:
        df = fallback_df

    analysis = analyze_market_strictly(df, comm_name, sensitivity_choice)
    return {
        "name": comm_name,
        "contract_symbol": contract_symbol,
        "quote_meta": quote_meta,
        "global_meta": global_meta,
        "analysis": analysis
    }


with ThreadPoolExecutor(max_workers=2) as executor:
    f_ng = executor.submit(load_complete_commodity, "Natural Gas")
    f_cr = executor.submit(load_complete_commodity, "Crude Oil")
    ng_bundle = f_ng.result()
    crude_bundle = f_cr.result()


# ==============================================================================
# 11. RENDER COMPLETE COMMODITY TERMINAL PANEL
# ==============================================================================
def render_commodity_dashboard(bundle: dict):
    name = bundle["name"]
    contract = bundle["contract_symbol"]
    g_meta = bundle["global_meta"]
    an = bundle["analysis"]

    st.markdown(f"## 🔥 {name} (`{contract}`)")
    if not an:
        st.error("Market data currently initializing. Click Refresh.")
        return

    act = an["active_setup"]
    sig_log = an["signal_log"]
    live_ltp = an["ltp"]

    # ------------------------------------------------------------------
    # A. STRICT SETUP BANNER (ONLY SHOWS TRADE WHEN FRESH & CONFIRMED)
    # ------------------------------------------------------------------
    if act is None:
        last_sig_text = "Aaj ke session me abhi tak koi high-probability breakout trigger nahi hua hai."
        if sig_log:
            ls = sig_log[-1]
            ls_sig = ls["Signal"]
            ls_time = ls["Time (IST)"]
            ls_price = ls["Trigger Price"]
            ls_status = ls["Status"]
            last_sig_text = (
                f"📌 <b>Last Triggered Setup:</b> {ls_sig} at <b>{ls_time}</b> "
                f"(Entry ₹{ls_price}) — Status: <b>{ls_status}</b>"
            )

        st.markdown(f"""
        <div class="banner-wait">
            <h3 style="margin:0; color:#fbbf24;">🚫 NO NEW SETUP NOW — WAIT FOR CONFIRMATION</h3>
            <p style="margin:6px 0 0 0; font-size:0.95rem; color:#e2e8f0;">
                Is waqt current candle par koi fresh institutional trade setup nahi ban raha hai. Beech market me zabardasti entry mat lein.<br>
                <span style="color:#94a3b8; font-size:0.88rem;">🕒 Live Scan Time: <b>{now_ist_str}</b> &nbsp;|&nbsp; {last_sig_text}</span>
            </p>
        </div>
        """, unsafe_allow_html=True)

    elif act["Signal"] == "BUY":
        mins_ago = max(0, int((now_ist - act["timestamp_dt"]).total_seconds() // 60))
        setup_time_ist = act["Time (IST)"]
        trig_price = act["Trigger Price"]
        sl_price = act["Stop Loss"]
        t1_price = act["Target 1"]
        t2_price = act["Target 2"]

        st.markdown(f"""
        <div class="banner-buy">
            <h3 style="margin:0; color:#34d399;">🟢 CONFIRMED BUY SETUP ACTIVE — {name.upper()}</h3>
            <p style="margin:8px 0 0 0; font-size:1.0rem;">
                ⏰ <b>Exact Setup Candle Time:</b> <span style="background:#065f46; padding:2px 8px; border-radius:4px;">{setup_time_ist} IST ({mins_ago} mins ago)</span><br>
                🎯 <b>Trigger Entry:</b> ₹{trig_price} (Live: ₹{live_ltp}) &nbsp;|&nbsp;
                🛑 <b>Stop Loss:</b> ₹{sl_price} &nbsp;|&nbsp;
                ✅ <b>Target 1:</b> ₹{t1_price} &nbsp;|&nbsp;
                🚀 <b>Target 2:</b> ₹{t2_price}
            </p>
        </div>
        """, unsafe_allow_html=True)

    elif act["Signal"] == "SELL":
        mins_ago = max(0, int((now_ist - act["timestamp_dt"]).total_seconds() // 60))
        setup_time_ist = act["Time (IST)"]
        trig_price = act["Trigger Price"]
        sl_price = act["Stop Loss"]
        t1_price = act["Target 1"]
        t2_price = act["Target 2"]

        st.markdown(f"""
        <div class="banner-sell">
            <h3 style="margin:0; color:#f87171;">🔴 CONFIRMED SELL SETUP ACTIVE — {name.upper()}</h3>
            <p style="margin:8px 0 0 0; font-size:1.0rem;">
                ⏰ <b>Exact Setup Candle Time:</b> <span style="background:#991b1b; padding:2px 8px; border-radius:4px;">{setup_time_ist} IST ({mins_ago} mins ago)</span><br>
                🎯 <b>Trigger Entry:</b> ₹{trig_price} (Live: ₹{live_ltp}) &nbsp;|&nbsp;
                🛑 <b>Stop Loss:</b> ₹{sl_price} &nbsp;|&nbsp;
                ✅ <b>Target 1:</b> ₹{t1_price} &nbsp;|&nbsp;
                🚀 <b>Target 2:</b> ₹{t2_price}
            </p>
        </div>
        """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # B. TOP METRICS BAR (MCX LIVE + VWAP + SUPERTREND + GLOBAL NYMEX)
    # ------------------------------------------------------------------
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("MCX Live LTP", f"₹ {an['ltp']}", delta=f"{round(an['ltp'] - an['vwap'], 2)} vs VWAP")
    m2.metric("Session VWAP", f"₹ {an['vwap']}", delta="Above VWAP" if an["ltp"] > an["vwap"] else "Below VWAP")
    m3.metric("Supertrend (10,3)", f"₹ {an['supertrend']}", delta="BULLISH" if an["st_dir"] == 1 else "BEARISH")
    m4.metric("RSI / ADX", f"{an['rsi']} / {an['adx']}", delta="Trending" if an["adx"] >= 20 else "Sideways Chop")
    g_px = g_meta.get("global_price", "N/A")
    g_chg = g_meta.get("global_chg_pct", 0.0)
    m5.metric("NYMEX Global", f"$ {g_px}", delta=f"{g_chg}%")

    # ------------------------------------------------------------------
    # C. CHART WITH EXACT BUY/SELL TIMESTAMP LABELS
    # ------------------------------------------------------------------
    render_institutional_chart(an, f"{name} ({contract})")

    # ------------------------------------------------------------------
    # D. TABS: 1) STRICT CHECKLIST  2) TODAY'S SIGNAL LOG  3) PIVOTS & OPTIONS
    # ------------------------------------------------------------------
    t1, t2, t3 = st.tabs([
        "🔍 Live 6-Point Confirmation Checklist",
        "🕒 Signal History & Timestamps",
        "🎯 Option Strike & Pivot Levels (CPR)"
    ])

    with t1:
        st.caption("Jab tak niche diye gaye sabhi conditions ek sath green (`PASS`) nahi hote aur fresh breakout nahi aata, tab tak terminal naya trade suggest nahi karega:")
        for status_code, desc in an["checklist"]:
            if status_code == "PASS":
                st.markdown(f"✅ <span class='check-pass'>{desc}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"⏳ <span class='check-wait'>{desc}</span>", unsafe_allow_html=True)

    with t2:
        st.caption("Pichle kuch sessions me kab-kab exact kis candle time par setup bana aur uska kya result raha:")
        if sig_log:
            log_df = pd.DataFrame(sig_log)[
                ["Time (IST)", "Signal", "Trigger Price", "Stop Loss", "Target 1", "Target 2", "RSI", "ADX", "Status"]
            ].iloc[::-1]
            st.dataframe(log_df, use_container_width=True, hide_index=True)
        else:
            st.info("Recent candles me koi strict setup trigger nahi hua hai.")

    with t3:
        piv = an["pivots"]
        opt_rec = get_option_and_lot_recommendation(name, an["ltp"], act, risk_per_trade_inr)

        r2_v, r1_v = piv["R2"], piv["R1"]
        tc_v, p_v, bc_v = piv["TC"], piv["P"], piv["BC"]
        s1_v, s2_v = piv["S1"], piv["S2"]

        p_col1, p_col2 = st.columns(2)
        with p_col1:
            st.markdown("**📊 Intraday Floor Pivots & CPR Levels**")
            st.markdown(f"""
            <div class="level-box">
                🔴 <b>Resistance 2 (R2):</b> ₹{r2_v} &nbsp;|&nbsp; <b>Resistance 1 (R1):</b> ₹{r1_v}<br>
                🟣 <b>CPR Zone:</b> TC ₹{tc_v} — <b>Pivot ₹{p_v}</b> — BC ₹{bc_v}<br>
                🟢 <b>Support 1 (S1):</b> ₹{s1_v} &nbsp;|&nbsp; <b>Support 2 (S2):</b> ₹{s2_v}
            </div>
            """, unsafe_allow_html=True)

        with p_col2:
            st.markdown("**⚡ Option Strike & Position Sizing**")
            if opt_rec["status"] == "WAIT":
                opt_msg = opt_rec["message"]
                opt_atm = opt_rec["atm"]
                st.markdown(f"""
                <div class="level-box">
                    🚫 <b>Option Action:</b> {opt_msg}<br>
                    📍 <b>Nearest ATM Strike:</b> {opt_atm} CE / {opt_atm} PE (Watch Only)
                </div>
                """, unsafe_allow_html=True)
            else:
                opt_type = opt_rec["opt_type"]
                atm_pick = opt_rec["atm_pick"]
                itm_pick = opt_rec["itm_pick"]
                rec_lots = opt_rec["rec_mini_lots"]
                risk_lot = opt_rec["risk_per_mini_lot"]
                st.markdown(f"""
                <div class="level-box">
                    ✅ <b>Direction:</b> {opt_type}<br>
                    🎯 <b>Best Strikes:</b> <b>{atm_pick}</b> or <b>{itm_pick}</b><br>
                    📦 <b>Recommended Mini Lots:</b> {rec_lots} Lot(s) (Risk ~₹{risk_lot}/lot)
                </div>
                """, unsafe_allow_html=True)


# Render Natural Gas & Crude Oil Side-by-Side
left_panel, right_panel = st.columns(2)
with left_panel:
    render_commodity_dashboard(ng_bundle)
with right_panel:
    render_commodity_dashboard(crude_bundle)

# Auto-refresh loop if toggled on
if auto_refresh:
    time.sleep(30)
    st.rerun()
