import streamlit as st
import feedparser
import yfinance as yf
import streamlit.components.v1 as components
import plotly.graph_objects as go
from datetime import datetime
import pytz

st.set_page_config(page_title="MCX Terminal Ultra-Fast", page_icon="⛽", layout="wide")

# --- TOP NAVIGATION ---
st.markdown("## ⛽ MCX Pro Terminal & Intelligence Engine")
nav_page = st.radio(
    "PAGES / SECTIONS:",
    [
        "🛢️ Live Terminal & Levels", 
        "🎯 Pattern Scanner & Setups", 
        "🧮 Risk, Lot & Brokerage Calculator", 
        "📑 OPEC & EIA Inventory", 
        "🚨 High Impact Hindi News"
    ],
    horizontal=True
)

st.markdown("---")

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)

# --- MARKET DATA & FAST PLOT ENGINE ---
@st.cache_data(ttl=60)
def get_market_overview(timeframe_code):
    try:
        tickers = yf.Tickers("INR=X DX-Y.NYB CL=F NG=F")
        usd_inr = tickers.tickers["INR=X"].history(period="1d")['Close'].iloc[-1]
        
        # DXY
        dxy_df = tickers.tickers["DX-Y.NYB"].history(period="2d")
        dxy_price = dxy_df['Close'].iloc[-1]
        dxy_prev = dxy_df['Close'].iloc[-2]
        dxy_change = ((dxy_price - dxy_prev) / dxy_prev) * 100

        def process_asset(t, conversion_factor):
            df = t.history(period="5d", interval=timeframe_code)
            if len(df) >= 20:
                # MCX Converted columns
                df['C_INR'] = df['Close'] * conversion_factor * (usd_inr / 83.5)
                df['O_INR'] = df['Open'] * conversion_factor * (usd_inr / 83.5)
                df['H_INR'] = df['High'] * conversion_factor * (usd_inr / 83.5)
                df['L_INR'] = df['Low'] * conversion_factor * (usd_inr / 83.5)
                df['SMA20'] = df['C_INR'].rolling(window=20).mean()

                curr = df.iloc[-1]
                prev = df.iloc[-2]
                price = curr['C_INR']
                prev_price = prev['C_INR']
                change_pct = ((price - prev_price) / prev_price) * 100

                # Pivot Levels
                h_prev = df['H_INR'].iloc[-2]
                l_prev = df['L_INR'].iloc[-2]
                c_prev = prev['C_INR']

                pivot = (h_prev + l_prev + c_prev) / 3
                r1 = (2 * pivot) - l_prev
                s1 = (2 * pivot) - h_prev
                r2 = pivot + (h_prev - l_prev)
                s2 = pivot - (h_prev - l_prev)

                trend = "BULLISH (Tezi)" if price > curr['SMA20'] else "BEARISH (Mandi)"
                patterns = scan_patterns(df)

                return {
                    "price": price,
                    "change": change_pct,
                    "trend": trend,
                    "sma": curr['SMA20'],
                    "pivot": pivot,
                    "r1": r1, "r2": r2,
                    "s1": s1, "s2": s2,
                    "patterns": patterns,
                    "df": df.tail(40) # Last 40 candles for lightning fast charting
                }
            return None

        crude = process_asset(tickers.tickers["CL=F"], 84.0)
        gas = process_asset(tickers.tickers["NG=F"], 83.5)
        return crude, gas, dxy_price, dxy_change
    except Exception:
        return None, None, 104.0, 0.0

def scan_patterns(df):
    detected = []
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    c_open, c_close, c_high, c_low = curr['O_INR'], curr['C_INR'], curr['H_INR'], curr['L_INR']
    p_open, p_close = prev['O_INR'], prev['C_INR']
    body = abs(c_close - c_open)
    lower_wick = min(c_open, c_close) - c_low
    upper_wick = c_high - max(c_open, c_close)

    if lower_wick > (1.8 * body) and upper_wick < (0.6 * body) and body > 0:
        entry = c_high + (body * 0.1)
        sl = c_low - (body * 0.1)
        risk = entry - sl
        detected.append({
            "name": "🔨 Bullish Hammer (Reversal Setup)", "type": "BUY",
            "time": "Latest Candle", "entry": entry, "sl": sl,
            "t1": entry + (risk * 1.5), "t2": entry + (risk * 2.0),
            "desc": "Niche se heavy buyer demand aayi hai. Bounce signal."
        })

    if upper_wick > (1.8 * body) and lower_wick < (0.6 * body) and body > 0:
        entry = c_low - (body * 0.1)
        sl = c_high + (body * 0.1)
        risk = sl - entry
        detected.append({
            "name": "🌠 Shooting Star (Bikwali Reversal)", "type": "SELL",
            "time": "Latest Candle", "entry": entry, "sl": sl,
            "t1": entry - (risk * 1.5), "t2": entry - (risk * 2.0),
            "desc": "Upar se heavy selling rejection. Mandi aane ke chances."
        })

    if p_close < p_open and c_close > c_open and c_close >= p_open:
        entry = c_high
        sl = min(c_low, prev['L_INR'])
        risk = entry - sl
        detected.append({
            "name": "🟢 Bullish Engulfing (Strong Buyers)", "type": "BUY",
            "time": "Latest Candle", "entry": entry, "sl": sl,
            "t1": entry + (risk * 1.5), "t2": entry + (risk * 2.0),
            "desc": "Green candle ne pichli red candle ko pura engulf kar liya hai."
        })

    if p_close > p_open and c_close < c_open and c_close <= p_open:
        entry = c_low
        sl = max(c_high, prev['H_INR'])
        risk = sl - entry
        detected.append({
            "name": "🔴 Bearish Engulfing (Strong Sellers)", "type": "SELL",
            "time": "Latest Candle", "entry": entry, "sl": sl,
            "t1": entry - (risk * 1.5), "t2": entry - (risk * 2.0),
            "desc": "Selling pressure badh gaya hai, breakdown indication."
        })

    return detected

# --- TIMEFRAME SELECTOR ---
tf_choice = st.selectbox(
    "⏱️ Timeframe:",
    ["15 Minute (Intraday Best)", "5 Minute (Fast Scalping)", "1 Hour (Safe Swing)"]
)
tf_map = {
    "5 Minute (Fast Scalping)": "5m",
    "15 Minute (Intraday Best)": "15m",
    "1 Hour (Safe Swing)": "60m"
}

crude_data, gas_data, dxy_val, dxy_chg = get_market_overview(tf_map[tf_choice])

# Function to render lightning-fast native Candlestick Chart
def render_fast_candlestick(df, name):
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['O_INR'],
        high=df['H_INR'],
        low=df['L_INR'],
        close=df['C_INR'],
        name="Candles",
        increasing_line_color='#26a69a', 
        decreasing_line_color='#ef5350'
    ))
    
    # 20 SMA line
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['SMA20'], 
        mode='lines', 
        name='20 SMA',
        line=dict(color='#ff9800', width=1.5)
    ))

    fig.update_layout(
        title=f"{name} Live Candlestick (Pure MCX ₹)",
        yaxis_title="Price (₹)",
        xaxis_rangeslider_visible=False,
        height=380,
        margin=dict(l=10, r=10, t=35, b=10),
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)

# ==================== PAGE 1: LIVE TERMINAL ====================
if nav_page == "🛢️ Live Terminal & Levels":
    # DXY BANNER
    st.markdown("#### 💵 US Dollar Index (DXY) Live Correlation")
    d1, d2, d3 = st.columns([1, 1, 2])
    d1.metric("DXY Index Rate", f"{dxy_val:.2f}", f"{dxy_chg:.2f}%")
    if dxy_chg > 0.15:
        d2.warning("🔴 DXY RISING (Bearish Pressure)")
        d3.info("Dollar majboot ho raha hai. Crude & Natural Gas me buyers trap ho sakte hain.")
    elif dxy_chg < -0.15:
        d2.success("🟢 DXY FALLING (Bullish Support)")
        d3.info("Dollar kamzor ho raha hai. Commodities me buying rally ko support milega.")
    else:
        d2.info("⚪ DXY NEUTRAL")
        d3.caption("Dollar stable hai. Commodities apne chart levels follow karengi.")

    st.markdown("---")
    
    t1, t2 = st.tabs(["🛢️ Crude Oil (MCX)", "🔥 Natural Gas (MCX)"])

    def display_asset_tab(data, name, unit):
        if not data:
            st.error("Market data load ho raha hai... Page refresh karein.")
            return

        r1, r2, r3 = st.columns(3)
        r1.metric(f"Current MCX Bhav ({unit})", f"₹{data['price']:.1f}", f"{data['change']:.2f}%")
        r2.metric(f"20 MA ({tf_choice})", f"₹{data['sma']:.1f}")
        r3.metric("Trend", data['trend'])

        st.markdown("#### 📍 Support & Resistance (Pure ₹ me)")
        l1, l2, l3, l4, l5 = st.columns(5)
        l1.metric("R2 (Strong Sell)", f"₹{data['r2']:.1f}")
        l2.metric("R1 (First Target)", f"₹{data['r1']:.1f}")
        l3.metric("Pivot (Center)", f"₹{data['pivot']:.1f}")
        l4.metric("S1 (First Bounce)", f"₹{data['s1']:.1f}")
        l5.metric("S2 (Strong Buyer)", f"₹{data['s2']:.1f}")

        st.markdown("---")
        # ULTRA-FAST NATIVE CHART
        render_fast_candlestick(data['df'], name)

    with t1:
        display_asset_tab(crude_data, "Crude Oil", "₹/bbl")
    with t2:
        display_asset_tab(gas_data, "Natural Gas", "₹/mmBtu")

# ==================== PAGE 2: PATTERNS ====================
elif nav_page == "🎯 Pattern Scanner & Setups":
    st.subheader(f"🎯 Pattern Scanner Engine ({tf_choice})")
    
    p1, p2 = st.tabs(["🛢️ Crude Oil Patterns", "🔥 Natural Gas Patterns"])

    def show_pat_view(data, name):
        if not data:
            st.error("Data load ho raha hai...")
            return
        if data['patterns']:
            st.success(f"🔥 {len(data['patterns'])} Reversal Patterns Detect Hue Hain!")
            for idx, p in enumerate(data['patterns']):
                st.markdown(f"### {idx+1}. {p['name']}")
                st.markdown(f"**Timing:** `{p['time']}` | **Logic:** {p['desc']}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Recommended Entry", f"₹{p['entry']:.1f}")
                c2.metric("Strict Stop-Loss (SL)", f"₹{p['sl']:.1f}")
                c3.metric("Target 1 (1:1.5)", f"₹{p['t1']:.1f}")
                c4.metric("Target 2 (1:2.0)", f"₹{p['t2']:.1f}")
                st.divider()
        else:
            st.info("⏳ Pichli candles me consolidation chal raha hai. S1/R1 breakout ya fresh pattern ka wait karein.")

    with p1:
        show_pat_view(crude_data, "Crude Oil")
    with p2:
        show_pat_view(gas_data, "Natural Gas")

# ==================== PAGE 3: CALCULATOR ====================
elif nav_page == "🧮 Risk, Lot & Brokerage Calculator":
    st.subheader("🧮 Position Size & Net Profit/Loss Calculator")
    st.caption("Bade loss aur over-trading se bachne ke liye exact numbers dekhein:")

    col_calc1, col_calc2 = st.columns(2)
    
    with col_calc1:
        asset_type = st.selectbox("Select Commodity:", ["Crude Oil (Mega - 100 bbl)", "Crude Oil (Mini - 10 bbl)", "Natural Gas (Mega - 1250 mmBtu)", "Natural Gas (Mini - 250 mmBtu)"])
        user_max_risk = st.number_input("Aapka Max Loss/Risk Tolerance (₹):", min_value=500, max_value=50000, value=2000, step=500)
        entry_p = st.number_input("Planned Entry Price (₹):", value=6300.0, step=5.0)
        sl_p = st.number_input("Planned Stop-Loss Price (₹):", value=6270.0, step=5.0)
        tgt_p = st.number_input("Planned Target Price (₹):", value=6360.0, step=5.0)

        lot_size = 100 if "Mega - 100" in asset_type else (10 if "Mini - 10" in asset_type else (1250 if "Mega - 1250" in asset_type else 250))
        pts_risk = abs(entry_p - sl_p)
        pts_gain = abs(tgt_p - entry_p)

        risk_per_lot = pts_risk * lot_size
        recommended_lots = max(1, int(user_max_risk // risk_per_lot)) if risk_per_lot > 0 else 1

    with col_calc2:
        st.markdown("#### 📊 Calculation Result:")
        total_risk_val = risk_per_lot * recommended_lots
        gross_profit = pts_gain * lot_size * recommended_lots
        est_taxes = 75.0 * recommended_lots
        net_profit = gross_profit - est_taxes
        net_loss = total_risk_val + est_taxes

        st.metric("Recommended Lot Count:", f"{recommended_lots} Lot")
        st.metric("Total Stop-Loss Risk (₹):", f"-₹{net_loss:.1f}")
        st.metric("Target Hit Net Profit (₹):", f"+₹{net_profit:.1f}")

    st.markdown("---")
    st.subheader("🛡️ Pre-Trade Discipline Checklist")
    c_box1 = st.checkbox("1. Kya Candle Close hone par pattern confirm hua hai?")
    c_box2 = st.checkbox("2. Kya agle 30 minute me koi US EIA Inventory data nahi hai?")
    c_box3 = st.checkbox(f"3. Kya System me Stop-Loss (₹{sl_p:.1f}) lagane ke liye ready hain?")
    c_box4 = st.checkbox("4. Kya Risk-to-Reward ratio kam se kam 1:1.5 hai?")

    if c_box1 and c_box2 and c_box3 and c_box4:
        st.success("🟢 ALL CLEAR! Disciplined trade plan ke mutabiq execute karein.")
    else:
        st.warning("⚠️ RULES INCOMPLETE: Emotion me aakar trade na lein.")

# ==================== PAGE 4: OPEC & EIA ====================
elif nav_page == "📑 OPEC & EIA Inventory":
    st.subheader("📑 OPEC+ Policy & Weekly US EIA Storage Guide")
    
    weekday = now_ist.weekday()
    if weekday == 2:
        st.warning("🚨 AAJ CRUDE OIL INVENTORY HAI! (Raat 8:00 / 8:30 PM IST). Data time trade avoid karein.")
    elif weekday == 3:
        st.warning("🚨 AAJ NATURAL GAS INVENTORY HAI! (Raat 8:00 PM IST). Heavy spikes ka dhyan rakhein.")
    else:
        st.info("✅ Aaj koi major regular weekly inventory report nahi hai.")

    st.markdown("---")
    st.markdown("""
    * **🛢️ US EIA Crude Inventory (Wed):** Storage Badha = Mandi (Bearish) | Storage Ghati = Tezi (Bullish)
    * **🔥 EIA Natural Gas Storage (Thu):** Storage Badha = Mandi (Bearish) | Storage Ghati = Tezi (Bullish)
    * **🛢️ OPEC+ Meeting:** Production Cut = Strong Bullish Rally | Output Hike = Bearish
    """)

    st.markdown("---")
    st.subheader("📅 Live Economic Calendar (Investing.com)")
    cal_html = """
    <iframe src="https://sslecal2.investing.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&importance=2,3&features=datepicker,timezone&countries=5&calType=week&timeZone=55&lang=1" width="100%" height="450" frameborder="0"></iframe>
    """
    components.html(cal_html, height=460)

# ==================== PAGE 5: NEWS ====================
elif nav_page == "🚨 High Impact Hindi News":
    st.subheader("🚨 Global Market News & Direct Hindi Impact")
    st.caption("Khabrein aur unka bhav par direct asar:")

    feed = feedparser.parse("https://feeds.finance.yahoo.com/rss/2.0/headline?s=CL=F,NG=F&region=US&lang=en-US")
    for item in feed.entries[:8]:
        t = item.title.lower()
        if "opec" in t:
            tag = "OPEC IMPACT"
            asar = "OPEC cut se tezi aur production badhane se mandi aati hai."
        elif "tariff" in t or "trump" in t:
            tag = "HIGH VOLATILITY ALERT"
            asar = "Trump / Tariff se achanak sharp panic drop aa sakta hai. Stop-loss lagakar rakhein."
        elif "war" in t or "strike" in t or "middle east" in t:
            tag = "BULLISH BIAS"
            asar = "War tension se energy supply rukne ka darr hai -> Crude aur Gas me up-spike aayega."
        elif "drop" in t or "fall" in t or "slide" in t:
            tag = "BEARISH BIAS"
            asar = "Global demand kamzor hone ki chinta se selling dabav bana hua hai."
        else:
            tag = "NEUTRAL"
            asar = "Market normal chart levels follow karegi."

        st.markdown(f"#### 📰 {item.title}")
        st.markdown(f"👉 **Bhav Par Seedha Asar:** `{tag}` — {asar}")
        st.caption(f"Time: {item.get('published', '')}")
        st.divider()
             
