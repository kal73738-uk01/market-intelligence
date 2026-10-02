import streamlit as st
import feedparser
import yfinance as yf
import streamlit.components.v1 as components

st.set_page_config(page_title="MCX Terminal & Pattern Hub", page_icon="⛽", layout="wide")

# --- TOP NAVIGATION (MOBILE FRIENDLY TABS AS PAGES) ---
st.markdown("## ⛽ MCX Commodity Terminal & Pattern Engine")
nav_page = st.radio(
    "PAGES / SECTIONS:",
    ["🛢️ Live Terminal & Levels", "🎯 Dedicated Pattern & Trade Scanner", "📑 OPEC & EIA Inventory", "🚨 High Impact Hindi News"],
    horizontal=True
)

st.markdown("---")

# --- TIMEFRAME SELECTOR ---
tf_col1, tf_col2 = st.columns([1, 2])
with tf_col1:
    tf_choice = st.selectbox(
        "⏱️ Timeframe Chunein:",
        ["15 Minute (Intraday Best)", "5 Minute (Fast Scalping)", "1 Hour (Safe Swing)"]
    )
tf_map = {
    "5 Minute (Fast Scalping)": "5m",
    "15 Minute (Intraday Best)": "15m",
    "1 Hour (Safe Swing)": "60m"
}

# --- FETCH MARKET DATA & SCAN PATTERNS ---
@st.cache_data(ttl=60)
def get_comprehensive_market_data(timeframe_code):
    try:
        usdinr_ticker = yf.Ticker("INR=X")
        usd_data = usdinr_ticker.history(period="1d")
        usd_inr = usd_data['Close'].iloc[-1] if len(usd_data) > 0 else 84.0

        def analyze_asset(symbol, conversion_factor):
            t = yf.Ticker(symbol)
            df = t.history(period="5d", interval=timeframe_code)
            if len(df) >= 20:
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

                # Multi-candle pattern scan
                patterns = scan_multiple_patterns(df)

                return {
                    "price": price,
                    "change": change_pct,
                    "trend": trend,
                    "sma": curr['SMA20'],
                    "pivot": pivot,
                    "r1": r1, "r2": r2,
                    "s1": s1, "s2": s2,
                    "patterns": patterns
                }
            return None

        crude = analyze_asset("CL=F", 84.0)
        gas = analyze_asset("NG=F", 83.5)
        return crude, gas
    except Exception:
        return None, None

def scan_multiple_patterns(df):
    detected = []
    
    # 1. Latest Candle Scan
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    c_open, c_close, c_high, c_low = curr['O_INR'], curr['C_INR'], curr['H_INR'], curr['L_INR']
    p_open, p_close = prev['O_INR'], prev['C_INR']
    body = abs(c_close - c_open)
    lower_wick = min(c_open, c_close) - c_low
    upper_wick = c_high - max(c_open, c_close)

    # Bullish Hammer
    if lower_wick > (1.8 * body) and upper_wick < (0.6 * body) and body > 0:
        entry = c_high + (body * 0.1)
        sl = c_low - (body * 0.1)
        risk = entry - sl
        detected.append({
            "name": "🔨 Bullish Hammer (Reversal Setup)",
            "type": "BUY",
            "time": "Latest Candle",
            "entry": entry, "sl": sl,
            "t1": entry + (risk * 1.5), "t2": entry + (risk * 2.0),
            "desc": "Niche ke level se strong buying rejection aayi hai. Bounce aane ki sambhavna."
        })

    # Shooting Star
    if upper_wick > (1.8 * body) and lower_wick < (0.6 * body) and body > 0:
        entry = c_low - (body * 0.1)
        sl = c_high + (body * 0.1)
        risk = sl - entry
        detected.append({
            "name": "🌠 Shooting Star (Bikwali Reversal)",
            "type": "SELL",
            "time": "Latest Candle",
            "entry": entry, "sl": sl,
            "t1": entry - (risk * 1.5), "t2": entry - (risk * 2.0),
            "desc": "Upar ke level se sellers ne supply feki hai. Mandi aane ke chances."
        })

    # Bullish Engulfing
    if p_close < p_open and c_close > c_open and c_close >= p_open:
        entry = c_high
        sl = min(c_low, prev['L_INR'])
        risk = entry - sl
        detected.append({
            "name": "🟢 Bullish Engulfing (Strong Buyers)",
            "type": "BUY",
            "time": "Latest Candle",
            "entry": entry, "sl": sl,
            "t1": entry + (risk * 1.5), "t2": entry + (risk * 2.0),
            "desc": "Green candle ne pichli red candle ko pura cover kar liya hai."
        })

    # Bearish Engulfing
    if p_close > p_open and c_close < c_open and c_close <= p_open:
        entry = c_low
        sl = max(c_high, prev['H_INR'])
        risk = sl - entry
        detected.append({
            "name": "🔴 Bearish Engulfing (Strong Sellers)",
            "type": "SELL",
            "time": "Latest Candle",
            "entry": entry, "sl": sl,
            "t1": entry - (risk * 1.5), "t2": entry - (risk * 2.0),
            "desc": "Red candle ne bulls ko daba diya hai. Breakdown ka sign."
        })

    # 2. Support / Resistance Breakout Pattern (Recent 5 Candles)
    recent_high = df['H_INR'].iloc[-6:-1].max()
    recent_low = df['L_INR'].iloc[-6:-1].min()

    if curr['C_INR'] > recent_high:
        entry = curr['C_INR']
        sl = recent_high - (recent_high * 0.005)
        risk = entry - sl
        detected.append({
            "name": "🚀 5-Candle High Breakout",
            "type": "BUY",
            "time": "Breakout Formed",
            "entry": entry, "sl": sl,
            "t1": entry + (risk * 1.5), "t2": entry + (risk * 2.0),
            "desc": "Price pichle 5 candles ke consolidation ko todkar upar nikli hai."
        })

    if curr['C_INR'] < recent_low:
        entry = curr['C_INR']
        sl = recent_low + (recent_low * 0.005)
        risk = sl - entry
        detected.append({
            "name": "⚠️ 5-Candle Low Breakdown",
            "type": "SELL",
            "time": "Breakdown Formed",
            "entry": entry, "sl": sl,
            "t1": entry - (risk * 1.5), "t2": entry - (risk * 2.0),
            "desc": "Price pichle 5 candles ke support ko todkar niche chali gayi hai."
        })

    return detected

crude_data, gas_data = get_comprehensive_market_data(tf_map[tf_choice])

# ========================================================
# PAGE 1: LIVE TERMINAL & FAST CHART
# ========================================================
if nav_page == "🛢️ Live Terminal & Levels":
    st.subheader("📊 Live MCX Commodity Rates & Pivot Levels")
    c_tab1, c_tab2 = st.tabs(["🛢️ Crude Oil (MCX)", "🔥 Natural Gas (MCX)"])

    def show_terminal(data, name, unit, symbol_tv):
        if not data:
            st.error("Market data refresh ho raha hai... Please thoda wait karein.")
            return

        # Rates
        r1, r2, r3 = st.columns(3)
        r1.metric(f"MCX Bhav ({unit})", f"₹{data['price']:.1f}", f"{data['change']:.2f}%")
        r2.metric(f"SMA 20 ({tf_choice})", f"₹{data['sma']:.1f}")
        r3.metric("Trend Status", data['trend'])

        # Levels
        st.markdown("#### 📍 Support & Resistance (Pure ₹ me)")
        l1, l2, l3, l4, l5 = st.columns(5)
        l1.metric("R2 (Strong Sell)", f"₹{data['r2']:.1f}")
        l2.metric("R1 (First Target)", f"₹{data['r1']:.1f}")
        l3.metric("Pivot (Center)", f"₹{data['pivot']:.1f}")
        l4.metric("S1 (First Bounce)", f"₹{data['s1']:.1f}")
        l5.metric("S2 (Strong Buyer)", f"₹{data['s2']:.1f}")

        st.markdown("---")
        st.markdown(f"#### 📈 {name} Fast Interactive Chart")
        st.caption("Agar chart slow ho to niche button dabakar full screen me kholen:")
        
        # Fast TradingView Embed
        chart_html = f"""
        <div style="height:350px;">
          <iframe src="https://s.tradingview.com/widgetembed/?symbol={symbol_tv}&interval={tf_map[tf_choice]}&theme=light&style=1&timezone=Asia%2FKolkata&locale=en" width="100%" height="350" frameborder="0"></iframe>
        </div>
        """
        components.html(chart_html, height=360)
        st.link_button(f"🔗 Open {name} Full Chart (Instant High-Speed)", f"https://in.tradingview.com/chart/?symbol={symbol_tv}")

    with c_tab1:
        show_terminal(crude_data, "Crude Oil", "₹/bbl", "MCX:CRUDEOIL1!")
    with c_tab2:
        show_terminal(gas_data, "Natural Gas", "₹/mmBtu", "MCX:NATURALGAS1!")

# ========================================================
# PAGE 2: DEDICATED PATTERN & EXACT TRADE SCANNER
# ========================================================
elif nav_page == "🎯 Dedicated Pattern & Trade Scanner":
    st.subheader(f"🎯 Pattern Scanner Engine ({tf_choice})")
    st.caption("Automated Pattern Detection with Strict Stop-Loss & Target Prices in ₹")

    p_tab1, p_tab2 = st.tabs(["🛢️ Crude Oil Patterns", "🔥 Natural Gas Patterns"])

    def show_patterns(data, name, unit):
        if not data:
            st.error("Data load ho raha hai...")
            return

        patterns = data['patterns']
        if patterns:
            st.success(f"🔥 {len(patterns)} High-Probability Patterns / Breakouts Detect Hue Hain!")
            for idx, p in enumerate(patterns):
                st.markdown(f"### {idx+1}. {p['name']}")
                st.markdown(f"**Timing:** `{p['time']}` | **Logic:** {p['desc']}")
                
                b1, b2, b3, b4 = st.columns(4)
                b1.metric("Recommended Entry", f"₹{p['entry']:.1f}")
                b2.metric("Strict Stop-Loss (SL)", f"₹{p['sl']:.1f}")
                b3.metric("Target 1 (1:1.5)", f"₹{p['t1']:.1f}")
                b4.metric("Target 2 (1:2.0)", f"₹{p['t2']:.1f}")
                st.divider()
        else:
            st.info(f"### ⏳ Current Candle: No High-Probability Pattern Formed\nPichli 5 candles me consolidation chal raha hai. Breakout ya S1/R1 level reach hone ka wait karein.")

        st.markdown("#### 📚 Pattern Quick Reference Guide (Kyu aur Kaise Kaam Karta Hai)")
        st.markdown("""
        * **🔨 Bullish Hammer:** Niche lambi wick ka matlab hai buyers ne prices ko kheench liya. Entry candle high ke upar, SL candle low ke niche.
        * **🟢 Bullish Engulfing:** Badi green candle pichli red candle ko khaa jati hai. Strong buying signal.
        * **🌠 Shooting Star:** Upar lambi wick ka matlab sellers ne trap kiya hai. Mandi aane ke chances.
        * **🚀 5-Candle High Breakout:** Range toot-te hi momentum tezi se aage badhta hai.
        """)

    with p_tab1:
        show_patterns(crude_data, "Crude Oil", "₹/bbl")
    with p_tab2:
        show_patterns(gas_data, "Natural Gas", "₹/mmBtu")

# ========================================================
# PAGE 3: OPEC & EIA INVENTORY
# ========================================================
elif nav_page == "📑 OPEC & EIA Inventory":
    st.subheader("📑 OPEC+ Meeting & EIA Storage Impact Guide")
    
    st.markdown("""
    ### 🛢️ OPEC+ Policy Direct Impact
    * **Production Cut (Kharidari Asar):** 🟢 **BULLISH** — Crude Oil me tezi aane ke direct chances.
    * **Production Hike (Bikwali Asar):** 🔴 **BEARISH** — Market me supply aane se Crude girta hai.
    * **No Change:** ⚪ **NEUTRAL** — Market technical chart ke levels follow karega.
    """)
    st.markdown("---")

    st.subheader("📊 US EIA Inventory Rules (Weekly)")
    e_col1, e_col2 = st.columns(2)
    with e_col1:
        st.markdown("""
        **🛢️ US Crude Inventory (Har Budhwar Raat 8:00 / 9:00 PM)**
        * **Storage Badha (+ Surplus):** 🔴 *Bearish* (Rate gir sakta hai)
        * **Storage Ghati (- Drawdown):** 🟢 *Bullish* (Rate chadhega)
        """)
    with e_col2:
        st.markdown("""
        **🔥 Natural Gas EIA Storage (Har Guruwar Raat 8:00 PM)**
        * **Storage Badha (+ Injection):** 🔴 *Bearish for Gas*
        * **Storage Ghati (- Withdrawal):** 🟢 *Bullish for Gas*
        """)
    st.markdown("---")

    st.subheader("📅 Live Economic Calendar (Investing.com)")
    st.caption("US EIA Inventory Numbers Live Yahan Aate Hain:")
    cal_html = """
    <iframe src="https://sslecal2.investing.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&importance=2,3&features=datepicker,timezone&countries=5&calType=week&timeZone=55&lang=1" width="100%" height="500" frameborder="0"></iframe>
    """
    components.html(cal_html, height=510)

# ========================================================
# PAGE 4: HIGH IMPACT HINDI NEWS
# ========================================================
elif nav_page == "🚨 High Impact Hindi News":
    st.subheader("🚨 Global Market News & Direct Hindi Impact")
    st.caption("Bhav par seedha kya asar padega:")

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
 
