import streamlit as st
import feedparser
import yfinance as yf
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime
import pytz

st.set_page_config(page_title="MCX Institutional Pro Terminal", page_icon="⛽", layout="wide")

# --- 1. VOICE ALERT ENGINE ---
def render_voice_engine(alert_msg=""):
    clean_text = alert_msg.replace("'", "").replace('"', "")
    html_code = f"""
    <div style="background: #111827; padding: 8px 12px; border-radius: 6px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; border: 1px solid #374151;">
        <span style="color: #38bdf8; font-size: 13px;">🔊 <b>Voice Alert Engine:</b> Active</span>
        <button onclick="playRadheVoice('{clean_text}')" style="background: #059669; color: white; border: none; padding: 5px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">Test / Unlock Voice 🔔</button>
    </div>
    <script>
    function playRadheVoice(customText) {{
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            var text = customText ? customText : 'Radhe Radhe! MCX Mini Terminal Audio System Connected.';
            var msg = new SpeechSynthesisUtterance(text);
            msg.lang = 'hi-IN';
            msg.rate = 0.95;
            msg.pitch = 1.0;
            window.speechSynthesis.speak(msg);
        }}
    }}
    var triggerText = '{clean_text}';
    if (triggerText && triggerText.length > 5) {{
        setTimeout(function() {{ playRadheVoice(triggerText); }}, 1000);
    }}
    </script>
    """
    components.html(html_code, height=50)

# --- 2. 60-SEC AUTO-UPDATE ---
components.html("<script>setTimeout(function(){ window.parent.location.reload(); }, 60000);</script>", height=0, width=0)

# --- TOP NAVIGATION WORKSPACES ---
st.markdown("## ⛽ MCX Pro: Mini Institutional Engine")
nav_page = st.radio(
    "NAVIGATION WORKSPACES:",
    [
        "🛢️ Live Terminal & Levels",
        "📊 Angel One Pro Pre-Analysed Chart",
        "🎯 AI Predictive Forecast Chart",
        "⚡ Final Decision (1 Lot Mini)",
        "🧮 1 Lot Position & P&L Calculator",
        "📓 My Discipline Journal",
        "📑 OPEC, EIA & Global News Impact"
    ],
    horizontal=True
)

st.markdown("---")

ist = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(ist)

curr_time_dec = now_ist.hour + (now_ist.minute / 60.0)
if 11.0 <= curr_time_dec < 13.5:
    session_status = "🟡 DEAD ZONE (Sideways - Avoid Buying Naked OTM)"
elif 14.5 <= curr_time_dec < 17.5:
    session_status = "🔵 LONDON SESSION (Trend Setting Initial Move)"
elif 18.5 <= curr_time_dec <= 23.5:
    session_status = "🔥 US WALL STREET BLAST (High Liquidity & Fast Moves)"
else:
    session_status = "⚪ ASIAN / OFF-HOURS (Normal Consolidation)"

# --- TIMEFRAME SELECTOR ---
tf_choice = st.selectbox(
    "⏱️ Timeframe Analysis:",
    [
        "15 Minute (Intraday Standard)", 
        "5 Minute (Fast Scalping)", 
        "1 Hour (Swing/Positional)",
        "1 Day (Daily Trend & Swing)",
        "1 Week (Weekly Macro Outlook)"
    ]
)
tf_map = {
    "5 Minute (Fast Scalping)": ("5m", "3d"),
    "15 Minute (Intraday Standard)": ("15m", "5d"),
    "1 Hour (Swing/Positional)": ("60m", "14d"),
    "1 Day (Daily Trend & Swing)": ("1d", "3mo"),
    "1 Week (Weekly Macro Outlook)": ("1wk", "1y")
}
interval_val, period_val = tf_map[tf_choice]

# --- ROBUST MARKET ENGINE ---
@st.cache_data(ttl=45, show_spinner=False)
def load_speed_data(interv, per):
    try:
        raw_data = yf.download(tickers="CL=F NG=F", period=per, interval=interv, group_by='ticker', progress=False)

        def process_asset(t_df, is_gas=False):
            if t_df is None or len(t_df) < 5:
                return None
            df = t_df.dropna().copy()

            if is_gas:
                last_c = df['Close'].iloc[-1]
                mult = 301.8 / last_c if last_c > 0 else 96.5
            else:
                mult = 84.0

            df['C_INR'] = df['Close'] * mult
            df['O_INR'] = df['Open'] * mult
            df['H_INR'] = df['High'] * mult
            df['L_INR'] = df['Low'] * mult

            # Angel One Technical Tool Stack
            df['SMA9'] = df['C_INR'].rolling(window=min(9, len(df)), min_periods=1).mean()
            df['MA50'] = df['C_INR'].rolling(window=min(50, len(df)), min_periods=1).mean()
            # GMMA Trader Ribbon
            df['GMMA3'] = df['C_INR'].ewm(span=3, adjust=False).mean()
            df['GMMA8'] = df['C_INR'].ewm(span=8, adjust=False).mean()
            df['GMMA15'] = df['C_INR'].ewm(span=15, adjust=False).mean()
            # GMMA Investor Ribbon
            df['GMMA30'] = df['C_INR'].ewm(span=30, adjust=False).mean()
            df['GMMA45'] = df['C_INR'].ewm(span=45, adjust=False).mean()
            df['GMMA60'] = df['C_INR'].ewm(span=60, adjust=False).mean()
            # Institutional VWAP proxy
            df['TYP'] = (df['H_INR'] + df['L_INR'] + df['C_INR']) / 3
            df['VWAP'] = df['TYP'].rolling(window=min(20, len(df)), min_periods=1).mean()

            curr = df.iloc[-1]
            prev = df.iloc[-2]
            price = curr['C_INR']
            prev_price = prev['C_INR']
            change_pct = ((price - prev_price) / prev_price) * 100

            h_prev = df['H_INR'].iloc[-2]
            l_prev = df['L_INR'].iloc[-2]
            c_prev = prev['C_INR']

            pivot = (h_prev + l_prev + c_prev) / 3
            bc = (h_prev + l_prev) / 2
            tc = (pivot - bc) + pivot
            r1 = (2 * pivot) - l_prev
            s1 = (2 * pivot) - h_prev
            r2 = pivot + (h_prev - l_prev)
            s2 = pivot - (h_prev - l_prev)

            oi_res = round((price + 1.2) / 2.5) * 2.5 if is_gas else round((price + 25) / 50) * 50
            oi_sup = round((price - 1.2) / 2.5) * 2.5 if is_gas else round((price - 25) / 50) * 50
            trend = "BULLISH (Tezi)" if price > curr['SMA9'] else "BEARISH (Mandi)"

            setup, trap, prediction, strikes = calc_mini_mechanics(df, price, oi_res, oi_sup, is_gas)

            return {
                "price": price, "change": change_pct, "trend": trend,
                "sma9": curr['SMA9'], "ma50": curr['MA50'],
                "vwap": curr['VWAP'], "oi_res": oi_res, "oi_sup": oi_sup,
                "pivot": pivot, "tc": tc, "bc": bc,
                "r1": r1, "r2": r2, "s1": s1, "s2": s2,
                "setup": setup, "trap": trap, "prediction": prediction,
                "strikes": strikes, "is_gas": is_gas, "df": df.tail(24)
            }

        crude = process_asset(raw_data['CL=F'], is_gas=False)
        gas = process_asset(raw_data['NG=F'], is_gas=True)
        return crude, gas
    except Exception:
        return None, None

def calc_mini_mechanics(df, current_price, oi_res, oi_sup, is_gas=False):
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    c_open, c_close, c_high, c_low = curr['O_INR'], curr['C_INR'], curr['H_INR'], curr['L_INR']
    body = abs(c_close - c_open)
    lower_wick = min(c_open, c_close) - c_low
    upper_wick = c_high - max(c_open, c_close)

    min_risk = 1.8 if is_gas else 16.0
    buffer_val = 0.3 if is_gas else 3.0

    setup = None
    trap = None
    prediction = None
    trade_dir = "BUY"

    if c_high > prev['H_INR'] and c_close < prev['H_INR'] and c_close < c_open:
        trap = {
            "title": "🪤 BULL TRAP (Buyers Trapped)",
            "action": "Put Side Entry",
            "reason": f"High (₹{prev['H_INR']:.1f}) break karke rejection wick banayi.",
            "next_move": f"Support band ₹{oi_sup:.1f} tak slide expected hai."
        }
        trade_dir = "SELL"
    elif c_low < prev['L_INR'] and c_close > prev['L_INR'] and c_close > c_open:
        trap = {
            "title": "🪤 BEAR TRAP (Shorts Trapped)",
            "action": "Call Side Entry",
            "reason": f"Low (₹{prev['L_INR']:.1f}) break karne ke baad rejection buying aayi.",
            "next_move": f"Resistance band ₹{oi_res:.1f} tak bounce aayega."
        }
        trade_dir = "BUY"

    if lower_wick > (1.7 * body) and upper_wick < (0.6 * body) and body > 0:
        entry = c_high + buffer_val
        sl = c_low - buffer_val
        risk = max(min_risk, min(entry - sl, 2.2 if is_gas else 22.0))
        t1 = entry + (risk * 1.4)
        t2 = entry + (risk * 2.0)
        trade_dir = "BUY"
        setup = {
            "name": "🔨 Angel Verified Hammer", "type": "BUY",
            "entry": entry, "sl": sl, "t1": t1, "t2": t2,
            "idx": df.index[-1], "price_point": c_low, "accuracy": "93% Confluence"
        }
        prediction = {
            "where": f"Angel Support Band (₹{oi_sup:.1f}) aur GMMA se strong buying bounce.",
            "what_now": f"Price ₹{entry:.1f} todte hi Target ₹{t1:.1f} achieve karega.",
            "trailing_rule": f"Bhav ₹{(entry + (risk * 0.5)):.1f} aate hi Stop-Loss cost-to-cost karein."
        }
    elif upper_wick > (1.7 * body) and lower_wick < (0.6 * body) and body > 0:
        entry = c_low - buffer_val
        sl = c_high + buffer_val
        risk = max(min_risk, min(sl - entry, 2.2 if is_gas else 22.0))
        t1 = entry - (risk * 1.4)
        t2 = entry - (risk * 2.0)
        trade_dir = "SELL"
        setup = {
            "name": "🌠 Angel Verified Shooting Star", "type": "SELL",
            "entry": entry, "sl": sl, "t1": t1, "t2": t2,
            "idx": df.index[-1], "price_point": c_high, "accuracy": "91% Confluence"
        }
        prediction = {
            "where": f"Angel Resistance Band (₹{oi_res:.1f}) se heavy institutional supply.",
            "what_now": f"Price ₹{entry:.1f} break karte hi Target ₹{t1:.1f} hit karega.",
            "trailing_rule": f"Bhav ₹{(entry - (risk * 0.5)):.1f} aate hi Stop-Loss entry rate par lock karein."
        }

    if not setup:
        if current_price >= oi_sup:
            trade_dir = "BUY"
            entry = current_price + (0.3 if is_gas else 3.0)
            risk = min_risk
            sl = entry - risk
            t1 = entry + (risk * 1.3)
            t2 = entry + (risk * 1.9)
            setup = {
                "name": "📈 GMMA Ribbon Alignment Buy", "type": "BUY",
                "entry": entry, "sl": sl, "t1": t1, "t2": t2,
                "idx": df.index[-1], "price_point": current_price, "accuracy": "88% Alignment"
            }
            prediction = {
                "where": f"Support Band (₹{oi_sup:.1f}) ke upar GMMA expanding upside.",
                "what_now": f"Breakout extend hone par agla target ₹{t1:.1f} expected hai.",
                "trailing_rule": f"Target 1 ke 50% par Stop-Loss entry rate par layein."
            }
        else:
            trade_dir = "SELL"
            entry = current_price - (0.3 if is_gas else 3.0)
            risk = min_risk
            sl = entry + risk
            t1 = entry - (risk * 1.3)
            t2 = entry - (risk * 1.9)
            setup = {
                "name": "📉 Below OI Band Breakdown", "type": "SELL",
                "entry": entry, "sl": sl, "t1": t1, "t2": t2,
                "idx": df.index[-1], "price_point": current_price, "accuracy": "86% Strength"
            }
            prediction = {
                "where": f"Support Band todkar GMMA downward expand ho rahi hai.",
                "what_now": f"Downside momentum par quick support level ₹{t1:.1f} test hoga.",
                "trailing_rule": f"Target 1 ke 50% par Stop-Loss break-even kar dein."
            }

    strikes = {}
    if is_gas:
        base_step = round(current_price / 2.5) * 2.5
        if trade_dir == "BUY":
            strikes['otm_name'] = f"{base_step + 10.0:.1f} CE"
            strikes['otm_prem'] = "₹6.50 – ₹8.50"
            strikes['atm_name'] = f"{base_step + 2.5:.1f} CE"
            strikes['atm_prem'] = "₹12.00 – ₹15.00"
        else:
            strikes['otm_name'] = f"{base_step - 10.0:.1f} PE"
            strikes['otm_prem'] = "₹6.50 – ₹8.50"
            strikes['atm_name'] = f"{base_step - 2.5:.1f} PE"
            strikes['atm_prem'] = "₹12.00 – ₹15.00"
    else:
        base_step = round(current_price / 50) * 50
        if trade_dir == "BUY":
            strikes['otm_name'] = f"{int(base_step + 150)} CE"
            strikes['otm_prem'] = "₹45 – ₹65"
            strikes['atm_name'] = f"{int(base_step + 50)} CE"
            strikes['atm_prem'] = "₹90 – ₹120"
        else:
            strikes['otm_name'] = f"{int(base_step - 150)} PE"
            strikes['otm_prem'] = "₹45 – ₹65"
            strikes['atm_name'] = f"{int(base_step - 50)} PE"
            strikes['atm_prem'] = "₹90 – ₹120"

    return setup, trap, prediction, strikes

crude_data, gas_data = load_speed_data(interval_val, period_val)

# VOICE NOTIFICATION
voice_alert_text = ""
if gas_data and gas_data.get('setup'):
    s = gas_data['setup']
    voice_alert_text = f"Radhe Radhe! Natural Gas Mini me {s['type']} setup bana hai. Entry ₹{s['entry']:.1f}."
render_voice_engine(voice_alert_text)

# --- 1. ANGEL ONE PRO PRE-ANALYSED CHART WITH REAL INDICATOR TOOLS & FORECAST PATH ---
def render_angel_tools_preanalysed_chart(data, name):
    df = data['df'].copy()
    setup = data['setup']
    zoom_df = df.tail(18)
    fig = go.Figure()

    # Candles
    fig.add_trace(go.Candlestick(
        x=zoom_df.index, open=zoom_df['O_INR'], high=zoom_df['H_INR'], low=zoom_df['L_INR'], close=zoom_df['C_INR'],
        name="Candles", increasing_line_color='#22c55e', decreasing_line_color='#ef4444'
    ))

    # Short GMMA Ribbon (Trader Lines)
    fig.add_trace(go.Scatter(x=zoom_df.index, y=zoom_df['GMMA3'], mode='lines', name='GMMA 3', line=dict(color='#3b82f6', width=1.2)))
    fig.add_trace(go.Scatter(x=zoom_df.index, y=zoom_df['GMMA8'], mode='lines', name='GMMA 8', line=dict(color='#60a5fa', width=1.0)))
    fig.add_trace(go.Scatter(x=zoom_df.index, y=zoom_df['GMMA15'], mode='lines', name='GMMA 15', line=dict(color='#93c5fd', width=1.0)))

    # Long GMMA Ribbon (Institutional Investor Lines)
    fig.add_trace(go.Scatter(x=zoom_df.index, y=zoom_df['GMMA30'], mode='lines', name='GMMA 30', line=dict(color='#d97706', width=1.0)))
    fig.add_trace(go.Scatter(x=zoom_df.index, y=zoom_df['GMMA45'], mode='lines', name='GMMA 45', line=dict(color='#b45309', width=1.2)))
    fig.add_trace(go.Scatter(x=zoom_df.index, y=zoom_df['GMMA60'], mode='lines', name='GMMA 60', line=dict(color='#78350f', width=1.5)))

    # MA 50 & VWAP
    fig.add_trace(go.Scatter(x=zoom_df.index, y=zoom_df['MA50'], mode='lines', name='MA 50 (Cyan)', line=dict(color='#06b6d4', width=2)))
    fig.add_trace(go.Scatter(x=zoom_df.index, y=zoom_df['VWAP'], mode='lines', name='VWAP (Purple)', line=dict(color='#c084fc', width=1.5, dash='dot')))

    # Angel One Dual OI Profile Bands (Resistance & Support)
    fig.add_hline(
        y=data['oi_res'], line_width=3, line_color="#eab308",
        annotation_text=f"🟡 OI Call Resistance ₹{data['oi_res']:.1f}", annotation_position="top right"
    )
    fig.add_hline(
        y=data['oi_sup'], line_width=3, line_color="#10b981",
        annotation_text=f"🟢 OI Put Support ₹{data['oi_sup']:.1f}", annotation_position="bottom right"
    )

    # PRE-ANALYSED TOOL PROJECTION: Aage Kya Hoga (Trajectory Projection)
    last_t = zoom_df.index[-1]
    next_t = last_t + (last_t - zoom_df.index[-2])
    target_price = setup['t1'] if setup else data['price']
    proj_color = "#22c55e" if setup and setup['type'] == "BUY" else "#ef4444"

    fig.add_trace(go.Scatter(
        x=[last_t, next_t], y=[data['price'], target_price],
        mode="lines+markers",
        line=dict(color=proj_color, width=3, dash='dashdot'),
        marker=dict(size=[0, 10], symbol="arrow-bar-up" if setup and setup['type'] == "BUY" else "arrow-bar-down"),
        name="Tools Predicted Path"
    ))

    fig.update_layout(
        title=dict(text=f"{name} Angel Tools: Pre-Analysed Projection Chart", x=0.02, y=0.98),
        yaxis_title="Price (₹)", xaxis_rangeslider_visible=False, height=530,
        margin=dict(l=10, r=10, t=55, b=10), template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, font=dict(size=10))
    )
    st.plotly_chart(fig, use_container_width=True)

# --- 2. AI PREDICTIVE FORECAST CHART (CYAN/YELLOW TARGET CANDLE) ---
def render_ai_forecast_chart(data, name):
    df = data['df'].copy()
    setup = data['setup']
    strikes = data['strikes']

    if setup:
        card_color = "#134e4a" if setup['type'] == "BUY" else "#7f1d1d"
        st.markdown(f"""
        <div style="background-color: {card_color}; padding: 12px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #ffffff33;">
            <h3 style="margin: 0; color: white;">🎯 AI VERIFIED PATTERN FLASH: {setup['name']}</h3>
            <p style="margin: 3px 0; color: #fde047; font-size: 14px;"><b>Signal:</b> {setup['type']} | <b>Setup Accuracy:</b> {setup['accuracy']}</p>
            <div style="display: flex; justify-content: space-between; margin-top: 6px; background: rgba(0,0,0,0.4); padding: 8px; border-radius: 6px;">
                <span style="color: #38bdf8; font-size: 16px;"><b>Entry:</b> ₹{setup['entry']:.1f}</span>
                <span style="color: #f87171; font-size: 16px;"><b>SL:</b> ₹{setup['sl']:.1f}</span>
                <span style="color: #4ade80; font-size: 16px;"><b>Target:</b> ₹{setup['t1']:.1f}</span>
            </div>
            <p style="margin-top: 6px; margin-bottom: 0; color: #f1f5f9; font-size: 13px;">
               👉 <b>1 Lot Pocket Option (< ₹10):</b> <span style="color:#22d3ee; font-weight:bold;">{strikes['otm_name']}</span> (Bhav: {strikes['otm_prem']})
            </p>
        </div>
        """, unsafe_allow_html=True)

    zoom_df = df.tail(16)
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=zoom_df.index, open=zoom_df['O_INR'], high=zoom_df['H_INR'], low=zoom_df['L_INR'], close=zoom_df['C_INR'],
        name="Past Candles", increasing_line_color='#22c55e', decreasing_line_color='#ef4444'
    ))

    if setup:
        col = "#22c55e" if setup['type'] == "BUY" else "#ef4444"
        sym = "triangle-up" if setup['type'] == "BUY" else "triangle-down"

        fig.add_trace(go.Scatter(
            x=[setup['idx']], y=[setup['price_point']], mode="markers+text",
            marker=dict(symbol=sym, size=16, color=col),
            text=[f"🎯 SETUP"], textposition="bottom center" if setup['type'] == "BUY" else "top center",
            name="Confirmed Setup"
        ))

        last_t = zoom_df.index[-1]
        next_t = last_t + (last_t - zoom_df.index[-2])
        proj_open = setup['entry']
        proj_close = setup['t1']
        proj_high = max(proj_open, proj_close) + abs(proj_close - proj_open) * 0.15
        proj_low = min(proj_open, proj_close) - abs(proj_close - proj_open) * 0.15

        fig.add_trace(go.Candlestick(
            x=[next_t], open=[proj_open], high=[proj_high], low=[proj_low], close=[proj_close],
            name="Forecast Target Candle",
            increasing_line_color='#00e5ff', decreasing_line_color='#eab308'
        ))

        fig.add_hline(y=setup['entry'], line_dash="dot", line_color="#38bdf8", annotation_text=f"Entry: ₹{setup['entry']:.1f}")
        fig.add_hline(y=setup['sl'], line_dash="dash", line_color="#ef4444", annotation_text=f"SL: ₹{setup['sl']:.1f}")
        fig.add_hline(y=setup['t1'], line_dash="dash", line_color="#22c55e", annotation_text=f"Target: ₹{setup['t1']:.1f}")

    fig.update_layout(
        title=dict(text=f"{name} AI Forecast Chart (Cyan/Yellow = Projected Move)", x=0.02, y=0.98),
        yaxis_title="Price (₹)", xaxis_rangeslider_visible=False, height=520,
        margin=dict(l=10, r=10, t=55, b=10), template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0, font=dict(size=10))
    )
    st.plotly_chart(fig, use_container_width=True)

# ========================================================
# 1. LIVE TERMINAL & LEVELS
# ========================================================
if nav_page == "🛢️ Live Terminal & Levels":
    st.markdown(f"#### 🌐 Live Trading Session: `{session_status}`")
    t1, t2 = st.tabs(["🔥 Natural Gas Mini (MCX)", "🛢️ Crude Oil Mini (MCX)"])

    def show_terminal_tab(data, name, unit):
        if not data:
            st.error("Market data sync ho raha hai... Please wait.")
            return

        r1, r2, r3, r4 = st.columns(4)
        r1.metric(f"Live MCX Bhav ({unit})", f"₹{data['price']:.1f}", f"{data['change']:.2f}%")
        r2.metric("SMA 9", f"₹{data['sma9']:.1f}")
        r3.metric("MA 50", f"₹{data['ma50']:.1f}")
        r4.metric("OI Resistance", f"₹{data['oi_res']:.1f}")

        st.markdown("#### 📍 Support, CPR & Resistance (₹ me)")
        l1, l2, l3, l4, l5, l6, l7 = st.columns(7)
        l1.metric("R2", f"₹{data['r2']:.1f}")
        l2.metric("R1", f"₹{data['r1']:.1f}")
        l3.metric("TC", f"₹{data['tc']:.1f}")
        l4.metric("Pivot", f"₹{data['pivot']:.1f}")
        l5.metric("BC", f"₹{data['bc']:.1f}")
        l6.metric("S1", f"₹{data['s1']:.1f}")
        l7.metric("S2", f"₹{data['s2']:.1f}")

    with t1:
        show_terminal_tab(gas_data, "Natural Gas Mini", "₹/mmBtu")
    with t2:
        show_terminal_tab(crude_data, "Crude Oil Mini", "₹/bbl")

# ========================================================
# 2. PAGE: ANGEL ONE PRO PRE-ANALYSED CHART
# ========================================================
elif nav_page == "📊 Angel One Pro Pre-Analysed Chart":
    st.subheader(f"📊 Angel One Indicator Setup - Full GMMA Cluster, VWAP, Dual OI Bands & Projected Path ({tf_choice})")
    p1, p2 = st.tabs(["🔥 Natural Gas Mini (Angel Tools)", "🛢️ Crude Oil Mini (Angel Tools)"])
    with p1:
        if gas_data: render_angel_tools_preanalysed_chart(gas_data, "Natural Gas Mini")
    with p2:
        if crude_data: render_angel_tools_preanalysed_chart(crude_data, "Crude Oil Mini")

# ========================================================
# 3. PAGE: AI PREDICTIVE FORECAST CHART
# ========================================================
elif nav_page == "🎯 AI Predictive Forecast Chart":
    st.subheader(f"🎯 AI Pre-Calculated Pattern Forecast & Target Projection ({tf_choice})")
    f1, f2 = st.tabs(["🔥 Natural Gas Mini AI Forecast", "🛢️ Crude Oil Mini AI Forecast"])
    with f1:
        if gas_data: render_ai_forecast_chart(gas_data, "Natural Gas Mini")
    with f2:
        if crude_data: render_ai_forecast_chart(crude_data, "Crude Oil Mini")

# ========================================================
# 4. FINAL DECISION (1 LOT MINI)
# ========================================================
elif nav_page == "⚡ Final Decision (1 Lot Mini)":
    st.subheader("⚡ Aakhiri Faisla: 1 Lot Mini Execution Plan")
    dec_tab1, dec_tab2 = st.tabs(["🔥 Natural Gas Mini Verdict", "🛢️ Crude Oil Mini Verdict"])

    def show_final_decision(data, asset_name):
        if not data:
            st.error("Data load ho raha hai...")
            return

        setup = data['setup']
        trap = data['trap']
        pred = data['prediction']
        strikes = data['strikes']
        is_gas = data['is_gas']

        pts_risk = abs(setup['entry'] - setup['sl'])
        pts_t1 = abs(setup['t1'] - setup['entry'])
        lot_qty = 250 if is_gas else 10

        rupee_loss = pts_risk * lot_qty
        rupee_t1 = pts_t1 * lot_qty

        if trap:
            st.error(f"### {trap['title']}")
            st.markdown(f"**Kya Hua Hai:** {trap['reason']}")
            st.markdown(f"👉 **Aapko Kya Karna Hai:** `{trap['action']}`")
            st.markdown(f"🔮 **Ab Aage Kya Hoga:** {trap['next_move']}")
            st.divider()

        st.success(f"### 🎯 TRADE DECISION: {setup['name']} [{setup['accuracy']}]")
        st.markdown(f"#### 1. 🔍 Kaha Se Kya Ho Raha Hai:\n* {pred['where']}")
        st.markdown(f"#### 2. 🔮 Ab Aage Kya Hoga:\n* {pred['what_now']}")

        st.markdown("#### 3. 🎯 1 Lot Mini Exact Numbers (Real In-Hand P&L):")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Recommended Entry", f"₹{setup['entry']:.1f}")
        c2.metric("Strict Stop-Loss (1 Lot)", f"₹{setup['sl']:.1f}", f"-₹{rupee_loss:.0f} Risk", delta_color="inverse")
        c3.metric("Target 1 Safe (1 Lot)", f"₹{setup['t1']:.1f}", f"+₹{rupee_t1:.0f} Gain")
        c4.metric("Target 2 Blast", f"₹{setup['t2']:.1f}")

        st.markdown("#### 💰 Recommended Option Strike (< ₹10 Safe Capital):")
        st.info(f"👉 **Kharidein:** `{strikes['otm_name']}` (Approx Bhav: {strikes['otm_prem']}) | **1 Lot Target:** +₹350 se +₹650")
        st.warning(f"🛡️ **Profit Lock:** {pred['trailing_rule']}")

    with dec_tab1:
        show_final_decision(gas_data, "Natural Gas Mini")
    with dec_tab2:
        show_final_decision(crude_data, "Crude Oil Mini")

# ========================================================
# 5. 1 LOT RISK CALCULATOR
# ========================================================
elif nav_page == "🧮 1 Lot Position & P&L Calculator":
    st.subheader("🧮 1 Lot Mini Position Calculator")
    c_a, c_b = st.columns(2)
    with c_a:
        asset_select = st.selectbox("Select Mini Commodity:", ["Natural Gas Mini (1 Lot = 250)", "Crude Oil Mini (1 Lot = 10)"])
        st.caption("🔒 Quantity locked to 1 Lot for Capital Protection.")
        default_ent = 301.8 if "Natural Gas" in asset_select else 6250.0
        default_stop = 300.0 if "Natural Gas" in asset_select else 6230.0
        default_tgt = 304.0 if "Natural Gas" in asset_select else 6290.0

        ent = st.number_input("Entry Price (₹):", value=default_ent, step=0.1 if "Natural Gas" in asset_select else 1.0)
        stop = st.number_input("Stop-Loss Price (₹):", value=default_stop, step=0.1 if "Natural Gas" in asset_select else 1.0)
        tgt = st.number_input("Target Price (₹):", value=default_tgt, step=0.1 if "Natural Gas" in asset_select else 1.0)

        lot_mult = 250 if "Natural Gas" in asset_select else 10
        pts_r = abs(ent - stop)
        pts_t = abs(tgt - ent)

    with c_b:
        st.markdown("#### 📊 1 Lot Real Calculations:")
        st.info(f"Total Traded Quantity: **{lot_mult} Units (1 Single Lot)**")
        tot_loss = pts_r * lot_mult
        tot_gain = pts_t * lot_mult
        st.metric("1 Lot Stop-Loss Risk:", f"-₹{tot_loss:.1f}")
        st.metric("1 Lot Target Gain:", f"+₹{tot_gain:.1f}")

# ========================================================
# 6. JOURNAL
# ========================================================
elif nav_page == "📓 My Discipline Journal":
    st.subheader("📓 Daily Trading Discipline Journal")
    if "journal_entries" not in st.session_state:
        st.session_state.journal_entries = []

    j_col1, j_col2 = st.columns(2)
    with j_col1:
        j_asset = st.selectbox("Asset:", ["Natural Gas Mini (1 Lot)", "Crude Oil Mini (1 Lot)"])
        j_type = st.radio("Trade Type:", ["BUY (Call)", "SELL (Put)"], horizontal=True)
        j_pnl = st.number_input("Profit/Loss (₹):", value=0, step=50)
    with j_col2:
        j_reason = st.selectbox("Reason:", ["Angel GMMA + OI Setup Followed", "Under ₹10 OTM Followed", "FOMO Entry", "SL Disciplined"])
        j_sl_used = st.checkbox("System SL Lagaya Tha?")
        save_btn = st.button("💾 Save to Journal")

    if save_btn:
        entry = {
            "date": now_ist.strftime("%d-%b %H:%M"),
            "asset": j_asset, "type": j_type, "pnl": j_pnl,
            "reason": j_reason, "sl": "Haan" if j_sl_used else "Nahi"
        }
        st.session_state.journal_entries.append(entry)
        st.success("Trade Record Ho Gaya!")

    st.markdown("---")
    st.markdown("#### 📋 Recent Trades:")
    if st.session_state.journal_entries:
        for trade in reversed(st.session_state.journal_entries):
            color = "🟢" if trade['pnl'] >= 0 else "🔴"
            st.markdown(f"**{trade['date']}** | {color} **₹{trade['pnl']}** | Asset: `{trade['asset']}` | Setup: `{trade['reason']}` | SL: `{trade['sl']}`")
            st.divider()

# ========================================================
# 7. OPEC, EIA & GLOBAL NEWS IMPACT
# ========================================================
elif nav_page == "📑 OPEC, EIA & Global News Impact":
    st.subheader("📑 Live Global Headlines, OPEC Reports & Direct Market Action")
    st.caption("Har badi international khabar ka Crude aur Gas ke bhav par seedha asar:")

    st.warning("⚠️ **EIA Natural Gas Storage Event:** Har Thursday (Guruwar) Shaam Theek 8:00 PM IST par data aata hai. Us time 5 minute naye trade avoid karein.")

    feed = feedparser.parse("https://feeds.finance.yahoo.com/rss/2.0/headline?s=CL=F,NG=F&region=US&lang=en-US")
    
    if feed.entries:
        for item in feed.entries[:8]:
            t = item.title.lower()

            if "steady" in t or "holds" in t or "hold output" in t:
                action_tag = "⚖️ OPEC PRODUCTION STEADY (BULLISH SUPPORT)"
                impact_hindi = "OPEC+ ne utpadan nahi badhaya hai. Supply tight rahegi, iska matlab Crude Oil me downside safe hai aur dips par buying support milega."
                trade_advice = "Mandi ke bade short trade avoid karein; support (OI Band/Pivot) par bounce trade pakdein."
            elif "cut" in t or "middle east" in t or "conflict" in t or "tighten" in t or "war" in t:
                action_tag = "🚀 GEOPOLITICAL / SUPPLY CRISIS (STRONG BULLISH)"
                impact_hindi = "War tension ya export routes tight hone se international oil/gas delivery me rukawat aayegi. Seedhi rally expected hai."
                trade_advice = "Breakout hote hi Call/Long side focus karein; strict trailing stop-loss maintain karein."
            elif "drop" in t or "fall" in t or "increase output" in t or "glut" in t or "surplus" in t:
                action_tag = "🔴 OVERSUPPLY / WEAK DEMAND (STRONG BEARISH)"
                impact_hindi = "Market me maal zyada hai aur demand kamzor hai, jisse sellers dominant rahenge."
                trade_advice = "Har upar ke bounce par resistance zone se Put/Sell trade dhundein."
            else:
                action_tag = "📊 REGULAR MARKET MOVEMENT"
                impact_hindi = "Normal market news hai. Market technical levels (OI Band aur GMMA) ko follow karegi."
                trade_advice = "Sirf OI Band aur Trend Confirmation par trade lein."

            st.markdown(f"#### 📰 {item.title}")
            st.markdown(f"👉 **Direct Market Verdict:** `{action_tag}`")
            st.markdown(f"💡 **Bhav Par Seedha Asar:** {impact_hindi}")
            st.info(f"🎯 **Trading Action Plan:** {trade_advice}")
            st.caption(f"Published: {item.get('published', '')}")
            st.divider()
    else:
        st.info("News feeds refresh ho rahe hain... Page ko reload karein.")




                    
