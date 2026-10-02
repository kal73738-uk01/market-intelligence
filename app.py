
import streamlit as st
import feedparser
import yfinance as yf
import streamlit.components.v1 as components

st.set_page_config(page_title="Ultimate Commodity Terminal", page_icon="⛽", layout="wide")

st.title("⛽ Ultimate Commodity & Intelligence Terminal")
st.caption("All-in-One: MCX Rates, Decision Signals, Levels, Investing.com Technicals & Calendar")

# --- DATA FETCHING & CALCULATIONS ---
def get_commodity_metrics(symbol, inr_multiplier):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="5d", interval="1d")
        
        # USD to INR fetch
        usdinr_ticker = yf.Ticker("INR=X")
        usdinr_df = usdinr_ticker.history(period="2d")
        usd_rate = usdinr_df['Close'].iloc[-1] if len(usdinr_df) > 0 else 84.0

        if len(df) >= 2:
            prev = df.iloc[-2]
            curr = df.iloc[-1]
            
            usd_price = curr['Close']
            prev_close = prev['Close']
            high = prev['High']
            low = prev['Low']
            close = prev['Close']
            
            # Pivot levels
            pivot = (high + low + close) / 3
            r1 = (2 * pivot) - low
            s1 = (2 * pivot) - high
            r2 = pivot + (high - low)
            s2 = pivot - (high - low)
            
            change = ((usd_price - prev_close) / prev_close) * 100
            trend = "BULLISH" if change > 0 else "BEARISH"
            
            # Indian MCX approximate conversion
            mcx_approx = usd_price * inr_multiplier * (usd_rate / 83.5)
            
            return {
                "usd_price": usd_price,
                "mcx_price": mcx_approx,
                "change": change,
                "trend": trend,
                "pivot": pivot,
                "r1": r1, "s1": s1,
                "r2": r2, "s2": s2
            }
    except Exception:
        pass
    return None

BULLISH_KEYWORDS = ["war", "cut", "strike", "escalat", "attack", "sanction", "outage", "tension", "gain", "rally"]
BEARISH_KEYWORDS = ["tariff", "truce", "ceasefire", "recession", "surplus", "slowdown", "hike", "threat", "drop", "dump"]

def fetch_global_news():
    feed = feedparser.parse("https://feeds.finance.yahoo.com/rss/2.0/headline?s=CL=F,NG=F&region=US&lang=en-US")
    news_items = []
    bullish_score = 0
    bearish_score = 0
    has_high_risk = False
    
    for entry in feed.entries[:6]:
        title = entry.title.lower()
        b_hits = sum(1 for w in BULLISH_KEYWORDS if w in title)
        be_hits = sum(1 for w in BEARISH_KEYWORDS if w in title)
        
        bullish_score += b_hits
        bearish_score += be_hits
        
        is_risk = "tariff" in title or "trump" in title or "threat" in title or "sanction" in title
        if is_risk:
            has_high_risk = True
            
        news_items.append({
            "title": entry.title,
            "link": entry.link,
            "risk": is_risk,
            "date": entry.get('published', '')
        })
        
    return news_items, bullish_score, bearish_score, has_high_risk

def generate_decision(trend, b_score, be_score, has_risk):
    if has_risk:
        return "⚠️ WAIT / NO-TRADE ZONE", "Global political statement / Tariff alert detect hua hai. Market unpredictable hai, trap se bachne ke liye trade hold karein.", "warning"
    if trend == "BULLISH":
        if be_score > b_score + 1:
            return "⚠️ WAIT (News-Trend Divergence)", "Chart Bullish hai par News negative hai. False breakout ka risk hai.", "warning"
        return "🟢 STRONG BUY ZONE", "Technical Trend Bullish hai aur news positive hai. Support (S1/Pivot) ke paas buying dekhein.", "success"
    else:
        if b_score > be_score + 1:
            return "⚠️ WAIT (News-Trend Divergence)", "Chart Bearish hai par news positive ban rahi hai. False dip ka khatra hai.", "warning"
        return "🔴 STRONG SELL ZONE", "Technical Trend Bearish hai aur market par selling pressure bana hua hai. Pullback par sell plan karein.", "error"

# Load Data
# Multiplier: Crude ~80-85 per bbl conversion, NG ~8.0-8.5
crude_info = get_commodity_metrics("CL=F", 84.0)
ng_info = get_commodity_metrics("NG=F", 83.0)
news_list, b_score, be_score, high_risk_flag = fetch_global_news()

# UI TABS
tab1, tab2, tab3 = st.tabs(["🛢️ CRUDE OIL TERMINAL", "🔥 NATURAL GAS TERMINAL", "📅 LIVE ECONOMIC CALENDAR"])

def render_terminal(info, name, unit, tv_symbol, inv_pair_id):
    if not info:
        st.error(f"{name} data abhi fetch nahi ho paya. Refresh karein.")
        return
        
    title, desc, alert_type = generate_decision(info['trend'], b_score, be_score, high_risk_flag)
    
    # 1. FINAL DECISION BOX
    st.subheader("🎯 Trade Decision Box")
    if alert_type == "success":
        st.success(f"### {title}\n**Kyu:** {desc}")
    elif alert_type == "error":
        st.error(f"### {title}\n**Kyu:** {desc}")
    else:
        st.warning(f"### {title}\n**Kyu:** {desc}")
        
    # 2. RATES (USD & MCX INR)
    col1, col2, col3 = st.columns(3)
    col1.metric("International Rate", f"${info['usd_price']:.2f}", f"{info['change']:.2f}%")
    col2.metric("Approx MCX India Rate", f"₹{info['mcx_price']:.1f}", f"{info['change']:.2f}%")
    col3.metric("Technical Trend", info['trend'])
    
    # 3. SUPPORT & RESISTANCE
    st.markdown("#### 📍 Support & Resistance Levels (Today)")
    l1, l2, l3, l4, l5 = st.columns(5)
    l1.metric("Resistance 2 (R2)", f"${info['r2']:.2f}")
    l2.metric("Resistance 1 (R1)", f"${info['r1']:.2f}")
    l3.metric("Pivot Level", f"${info['pivot']:.2f}")
    l4.metric("Support 1 (S1)", f"${info['s1']:.2f}")
    l5.metric("Support 2 (S2)", f"${info['s2']:.2f}")
    
    st.markdown("---")
    
    # 4. INVESTING.COM LIVE TECHNICAL SUMMARY & CHART
    st.subheader("📊 Investing.com Analysis & Live Candlestick")
    col_chart, col_meter = st.columns([2, 1])
    
    with col_chart:
        st.caption("Live Interactive Chart")
        chart_widget = f"""
        <!-- TradingView Widget BEGIN -->
        <div class="tradingview-widget-container" style="height:380px;">
          <iframe src="https://s.tradingview.com/widgetembed/?frameElementId=tradingview_7918a&symbol={tv_symbol}&interval=15&hidesidetoolbar=1&symboledit=0&saveimage=0&toolbarbg=f1f3f6&studies=[]&theme=light&style=1&timezone=Asia%2FKolkata" width="100%" height="380" frameborder="0" allowtransparency="true" scrolling="no"></iframe>
        </div>
        <!-- TradingView Widget END -->
        """
        components.html(chart_widget, height=390)
        
    with col_meter:
        st.caption("Investing.com Technical Summary Meter")
        investing_widget = f"""
        <iframe src="https://ssltscharts.investing.com/technical-summary/?pairs={inv_pair_id}&theme=light&lang=1" width="100%" height="380" frameborder="0"></iframe>
        """
        components.html(investing_widget, height=390)

with tab1:
    render_terminal(crude_info, "Crude Oil", "$/bbl", "NYMEX:CL1!", "8849")

with tab2:
    render_terminal(ng_info, "Natural Gas", "$/mmBtu", "NYMEX:NG1!", "8862")

with tab3:
    st.subheader("📅 Live Investing.com Economic Calendar")
    st.caption("US EIA Crude & Gas Inventory Reports (Time: Har Budhwar & Guruwar Raat)")
    calendar_widget = """
    <iframe src="https://sslecal2.investing.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&importance=2,3&features=datepicker,timezone&countries=5&calType=week&timeZone=55&lang=1" width="100%" height="550" frameborder="0" allowtransparency="true" marginwidth="0" marginheight="0"></iframe>
    """
    components.html(calendar_widget, height=560)

# 5. LIVE NEWS SCANNER
st.markdown("---")
st.subheader("🚨 Live Market Moving Headlines & Risk Scanner")
for item in news_list:
    badge = "⚠️ [GEO-POLITICAL / TARIFF RISK]" if item['risk'] else "📰 [MARKET UPDATE]"
    st.markdown(f"**{badge}** [{item['title']}]({item['link']})")
    st.caption(f"Time: {item['date']}")
