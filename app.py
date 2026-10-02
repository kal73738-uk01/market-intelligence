
    import streamlit as st
import feedparser
import yfinance as yf
import streamlit.components.v1 as components

st.set_page_config(page_title="MCX Terminal & Pattern Scanner", page_icon="⛽", layout="wide")

st.title("⛽ MCX Ultimate Terminal: Patterns, Levels & News Impact")
st.caption("Live Patterns, Exact Entry/SL/Target in ₹, Timeframe Technicals & Hindi Impact News")

# --- FETCH MARKET DATA & PATTERNS ---
@st.cache_data(ttl=60)
def get_market_analysis(timeframe_code):
    try:
        # USD-INR Fetch
        usdinr_ticker = yf.Ticker("INR=X")
        usd_data = usdinr_ticker.history(period="1d")
        usd_inr = usd_data['Close'].iloc[-1] if len(usd_data) > 0 else 84.0

        def process_asset(symbol, conversion_factor):
            t = yf.Ticker(symbol)
            df = t.history(period="5d", interval=timeframe_code)
            if len(df) >= 20:
                # Multiply to get MCX ₹ Prices
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

                # PATTERN DETECTION
                pattern_data = detect_candle_pattern(curr, prev, price)

                return {
                    "price": price,
                    "change": change_pct,
                    "trend": trend,
                    "sma": curr['SMA20'],
                    "pivot": pivot,
                    "r1": r1, "r2": r2,
                    "s1": s1, "s2": s2,
                    "pattern": pattern_data
                }
            return None

        crude = process_asset("CL=F", 84.0)
        gas = process_asset("NG=F", 83.5)
        return crude, gas, usd_inr
    except Exception:
        return None, None, 84.0

def detect_candle_pattern(curr, prev, price):
    c_open, c_close, c_high, c_low = curr['O_INR'], curr['C_INR'], curr['H_INR'], curr['L_INR']
    p_open, p_close = prev['O_INR'], prev['C_INR']
    body = abs(c_close - c_open)
    lower_wick = min(c_open, c_close) - c_low
    upper_wick = c_high - max(c_open, c_close)

    # 1. Bullish Hammer
    if lower_wick > (2 * body) and upper_wick < (0.5 * body) and body > 0:
        entry = c_high + (body * 0.1)
        sl = c_low - (body * 0.1)
        risk = entry - sl
        return {
            "name": "🔨 Bullish Hammer (Reversal Setup)",
            "type": "BUY",
            "entry": entry,
            "sl": sl,
            "t1": entry + (risk * 1.5),
            "t2": entry + (risk * 2.0),
            "desc": "Niche se strong buying rejection aayi hai. Reversal tezi ke sanket."
        }

    # 2. Bearish Shooting Star
    if upper_wick > (2 * body) and lower_wick < (0.5 * body) and body > 0:
        entry = c_low - (body * 0.1)
        sl = c_high + (body * 0.1)
        risk = sl - entry
        return {
            "name": "🌠 Shooting Star (Bikwali Reversal)",
            "type": "SELL",
            "entry": entry,
            "sl": sl,
            "t1": entry - (risk * 1.5),
            "t2": entry - (risk * 2.0),
            "desc": "Upar ke level se sellers ne trap kiya hai. Mandi aane ke chances."
        }

    # 3. Bullish Engulfing
    if p_close < p_open and c_close > c_open and c_close > p_open and c_open < p_close:
        entry = c_high
        sl = min(c_low, prev['L_INR'])
        risk = entry - sl
        return {
            "name": "🟢 Bullish Engulfing (Strong Buying)",
            "type": "BUY",
            "entry": entry,
            "sl": sl,
            "t1": entry + (risk * 1.5),
            "t2": entry + (risk * 2.0),
            "desc": "Pichli red candle ko green candle ne pura cover kar liya hai."
        }

    # 4. Bearish Engulfing
    if p_close > p_open and c_close < c_open and c_open > p_close and c_close < p_open:
        entry = c_low
        sl = max(c_high, prev['H_INR'])
        risk = sl - entry
        return {
            "name": "🔴 Bearish Engulfing (Strong Selling)",
            "type": "SELL",
            "entry": entry,
            "sl": sl,
            "t1": entry - (risk * 1.5),
            "t2": entry - (risk * 2.0),
            "desc": "Bulls ko bears ne daba diya hai, breakdown confirmation."
        }

    return None

# --- TIMEFRAME SELECTOR ---
st.markdown("### ⏱️ Timeframe Select Karein")
tf_choice = st.selectbox(
    "Candle Timeframe:",
    ["15 Minute (Intraday Regular)", "5 Minute (Fast Scalping)", "1 Hour (Safe Breakout)"]
)

tf_map = {
    "5 Minute (Fast Scalping)": "5m",
    "15 Minute (Intraday Regular)": "15m",
    "1 Hour (Safe Breakout)": "60m"
}

crude_data, gas_data, current_usd = get_market_analysis(tf_map[tf_choice])

# --- NEWS FETCHING ---
def get_hindi_news_impact():
    feed = feedparser.parse("https://feeds.finance.yahoo.com/rss/2.0/headline?s=CL=F,NG=F&region=US&lang=en-US")
    processed_news = []
    has_risk = False
    
    for item in feed.entries[:6]:
        t = item.title.lower()
        if "tariff" in t or "trump" in t:
            has_risk = True
            hindi_title = f"🔴 Trump / Tariff Bayan: {item.title}"
            asar = "Market me sudden sharp volatility aa sakti hai. Strict SL ke bina trade na lein."
            tag = "HIGH VOLATILITY ALERT"
        elif "war" in t or "strike" in t or "middle east" in t:
            hindi_title = f"⚔️ War / Tension Alert: {item.title}"
            asar = "Supply disruption fear -> Energy prices me up-spike aane ke chances."
            tag = "BULLISH BIAS"
        elif "drop" in t or "fall" in t or "slide" in t:
            hindi_title = f"📉 Global Selling Pressure: {item.title}"
            asar = "Demand chinta ke chalte mandi ka dabav bana hua hai."
            tag = "BEARISH BIAS"
        else:
            hindi_title = f"📰 Market Update: {item.title}"
            asar = "Normal technical levels follow honge."
            tag = "NEUTRAL"
            
        processed_news.append({"headline": hindi_title, "asar": asar, "tag": tag})
        
    return processed_news, has_risk

news_items, risk_flag = get_hindi_news_impact()

# --- TABS FOR COMMODITIES ---
tab1, tab2 = st.tabs(["🛢️ MCX Crude Oil Terminal", "🔥 MCX Natural Gas Terminal"])

def display_terminal_tab(data, name, unit, widget_symbol):
    if not data:
        st.error("Market data refresh ho raha hai... Thodi der me page refresh karein.")
        return
        
    # 1. RELIABLE PATTERN & SIGNAL BOX WITH SL / TARGET
    st.subheader(f"🎯 {name} - Pattern Signal & Exact Trade Setup")
    
    pat = data['pattern']
    if pat:
        box_type = st.success if pat['type'] == "BUY" else st.error
        box_type(f"### {pat['name']}\n**Explanation:** {pat['desc']}")
        
        c_p1, c_p2, c_p3, c_p4 = st.columns(4)
        c_p1.metric("Recommended Entry", f"₹{pat['entry']:.1f}")
        c_p2.metric("Strict Stop-Loss (SL)", f"₹{pat['sl']:.1f}")
        c_p3.metric("Target 1 (1:1.5)", f"₹{pat['t1']:.1f}")
        c_p4.metric("Target 2 (1:2.0)", f"₹{pat['t2']:.1f}")
    else:
        st.info(f"### ⏳ Current Candle: No High-Probability Pattern Formed\nAbhi fresh reliable reversal pattern nahi bana hai. Range breakout ya S1/R1 levels ka wait karein.")

    # 2. RISK FILTER
    if risk_flag:
        st.warning("⚠️ **Risk Alert:** Global political ya Tariff headline active hai, trade size chhota rakhein.")

    # 3. LIVE RATES & PIVOTS
    st.markdown("#### 💰 Live Rate & Trend")
    r1, r2, r3 = st.columns(3)
    r1.metric(f"Current Bhav ({unit})", f"₹{data['price']:.1f}", f"{data['change']:.2f}%")
    r2.metric("20 Moving Average", f"₹{data['sma']:.1f}")
    r3.metric("Trend Status", data['trend'])

    st.markdown("#### 📍 Support & Resistance (Pure ₹ me)")
    l1, l2, l3, l4, l5 = st.columns(5)
    l1.metric("Resistance 2 (R2)", f"₹{data['r2']:.1f}")
    l1.caption("Strong Selling Zone")
    l2.metric("Resistance 1 (R1)", f"₹{data['r1']:.1f}")
    l2.caption("First Hurdle")
    l3.metric("Pivot Level", f"₹{data['pivot']:.1f}")
    l3.caption("Mid Point")
    l4.metric("Support 1 (S1)", f"₹{data['s1']:.1f}")
    l4.caption("First Bounce Zone")
    l5.metric("Support 2 (S2)", f"₹{data['s2']:.1f}")
    l5.caption("Strong Buyer Zone")

    st.markdown("---")
    
    # 4. CHART
    st.subheader(f"📊 {name} Live Candlestick")
    tv_code = f"""
    <div style="height:380px;">
      <iframe src="https://s.tradingview.com/widgetembed/?symbol={widget_symbol}&interval={tf_map[tf_choice]}&theme=light&style=1&timezone=Asia%2FKolkata" width="100%" height="380" frameborder="0"></iframe>
    </div>
    """
    components.html(tv_code, height=390)

with tab1:
    display_terminal_tab(crude_data, "Crude Oil", "₹/Barrel", "MCX:CRUDEOIL1!")

with tab2:
    display_terminal_tab(gas_data, "Natural Gas", "₹/mmBtu", "MCX:NATURALGAS1!")

# --- HINDI IMPACT NEWS ---
st.markdown("---")
st.subheader("📰 Market Moving Headlines & Hindi Asar")
for item in news_items:
    st.markdown(f"**{item['headline']}**")
    st.markdown(f"👉 **Asar:** `{item['tag']}` — {item['asar']}")
    st.divider()
