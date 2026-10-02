import streamlit as st
import feedparser
import yfinance as yf

st.set_page_config(page_title="Market Intelligence Bot", page_icon="⛽", layout="wide")

st.title("⛽ Global Market Intelligence & Impact Meter")
st.caption("Crude Oil, Natural Gas, Global News & Inventory Impact Tracker")

st.subheader("📊 Live Asset Trends")
col1, col2 = st.columns(2)

def get_trend(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="5d", interval="1d")
        if len(df) >= 2:
            current_price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2]
            change = ((current_price - prev_price) / prev_price) * 100
            trend = "🟢 UPTREND (Bullish)" if change > 0 else "🔴 DOWNTREND (Bearish)"
            return current_price, change, trend
    except Exception:
        pass
    return 0.0, 0.0, "N/A"

crude_price, crude_change, crude_trend = get_trend("CL=F")
ng_price, ng_change, ng_trend = get_trend("NG=F")

with col1:
    st.metric(label="Crude Oil (WTI / MCX Track)", value=f"${crude_price:.2f}", delta=f"{crude_change:.2f}%")
    st.markdown(f"**Trend:** {crude_trend}")

with col2:
    st.metric(label="Natural Gas (Henry Hub / MCX Track)", value=f"${ng_price:.2f}", delta=f"{ng_change:.2f}%")
    st.markdown(f"**Trend:** {ng_trend}")

st.markdown("---")

st.subheader("📑 Weekly Inventory Reports Impact Guide")
r_col1, r_col2 = st.columns(2)

with r_col1:
    st.markdown("""
    **🛢️ US EIA Crude Oil Inventory (Har Budhwar Raat)**
    * **Storage Surplus (Stock Badha):** 🔴 *Bearish for Crude* (Supply zyada, rate gir sakte hain).
    * **Storage Drawdown (Stock Ghati):** 🟢 *Bullish for Crude* (Demand mazboot, rate badh sakte hain).
    """)

with r_col2:
    st.markdown("""
    **🔥 EIA Natural Gas Storage (Har Guruwar Raat)**
    * **Injection Expectation se Zyada:** 🔴 *Bearish for Nat Gas*.
    * **Withdrawal/Stock Kam:** 🟢 *Bullish for Nat Gas*.
    """)

st.markdown("---")

st.subheader("🚨 Live Global News & Sentiment Impact")

BULLISH_KEYWORDS = ["war", "cut", "strike", "escalat", "attack", "sanction", "outage", "tension"]
BEARISH_KEYWORDS = ["tariff", "truce", "ceasefire", "recession", "surplus", "slowdown", "hike", "threat"]

def analyze_impact(title):
    t_lower = title.lower()
    bullish_hits = [w for w in BULLISH_KEYWORDS if w in t_lower]
    bearish_hits = [w for w in BEARISH_KEYWORDS if w in t_lower]
    
    if "tariff" in t_lower or "trump" in t_lower:
        return "⚠️ HIGH VOLATILITY / BEARISH PRESSURE", "Trump statement / Tariff fear market sentiment par sudden dip la sakta hai. Long trade me tight SL rakhein."
    elif len(bullish_hits) > len(bearish_hits):
        return "🟢 BULLISH SIGNAL", "Geopolitical tension ya supply cut se crude/energy me tezi aane ke chances hain."
    elif len(bearish_hits) > len(bullish_hits):
        return "🔴 BEARISH SIGNAL", "Demand slowdown ya tariffs ki chinta se selling pressure ban sakta hai."
    else:
        return "⚪ NEUTRAL / OBSERVATION", "Normal update, trend follow karein."

news_feed = feedparser.parse("https://feeds.finance.yahoo.com/rss/2.0/headline?s=CL=F,NG=F&region=US&lang=en-US")

if news_feed.entries:
    for entry in news_feed.entries[:5]:
        impact_tag, analysis = analyze_impact(entry.title)
        with st.expander(f"{impact_tag} — {entry.title}"):
            st.write(f"**Asar (Market Impact):** {analysis}")
            st.caption(f"Published: {entry.get('published', '')}")
else:
    st.info("News feed load ho rahi hai...")

st.markdown("---")
st.caption("Refresh browser to fetch latest data.")
