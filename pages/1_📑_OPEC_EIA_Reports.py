import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="OPEC & EIA Reports", page_icon="📑", layout="wide")

st.title("📑 OPEC+ & US EIA Inventory Reports")
st.caption("Live Inventory Rules, OPEC Policy Impact & Economic Calendar")

# 1. OPEC GUIDE
st.subheader("🛢️ OPEC+ Meeting & Policy Impact")
st.markdown("""
* **OPEC Production Cut (Supply Ghatai):** 🟢 **BULLISH** — Crude Oil me ₹100–₹200 ki achanak rally aa sakti hai.
* **OPEC Output Hike (Supply Badhai):** 🔴 **BEARISH** — Supply badhne se Crude ke rates girte hain.
* **No Change (Status Quo):** ⚪ **NEUTRAL** — Market standard technical chart follow karega.
""")

st.markdown("---")

# 2. EIA STORAGE RULES
st.subheader("📊 US EIA Inventory Impact Rules")
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **🛢️ US Crude Inventory (Har Budhwar Raat 8:00/9:00 PM)**
    * **Storage Surplus (Stock Badha):** 🔴 *Bearish* (Supply zyada, Rate girega)
    * **Storage Drawdown (Stock Ghati):** 🟢 *Bullish* (Demand zyada, Rate chadhega)
    """)

with col2:
    st.markdown("""
    **🔥 EIA Natural Gas Storage (Har Guruwar Raat 8:00 PM)**
    * **Storage Badha (+ Injection):** 🔴 *Bearish for Gas*
    * **Storage Ghati (- Withdrawal):** 🟢 *Bullish for Gas*
    """)

st.markdown("---")

# 3. LIVE INVESTING.COM CALENDAR
st.subheader("📅 Live Economic Calendar (Investing.com)")
st.caption("EIA Crude & Gas actual release numbers live yahan check karein:")
cal_widget = """
<iframe src="https://sslecal2.investing.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&importance=2,3&features=datepicker,timezone&countries=5&calType=week&timeZone=55&lang=1" width="100%" height="500" frameborder="0" allowtransparency="true" marginwidth="0" marginheight="0"></iframe>
"""
components.html(cal_widget, height=520)
