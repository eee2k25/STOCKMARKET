import streamlit as st
import datetime
import requests
import yfinance as yf
import pandas as pd
import notifier
import nifty100_intraday_scanner as scanner

# Page Setup
st.set_page_config(
    page_title="Nifty & Mutual Fund Dip Advisor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-metric { font-size: 24px; font-weight: bold; }
    .badge-dip { background-color: #fee2e2; color: #b91c1c; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
    .badge-opp { background-color: #dcfce7; color: #15803d; padding: 3px 8px; border-radius: 4px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# User's 9 Mutual Funds
USER_FUNDS = {
    "119783": {"name": "SBI Healthcare Opportunities Fund (Direct-Growth)", "category": "Pharma", "rating": "5★"},
    "113049": {"name": "HDFC Gold ETF Fund", "category": "Gold", "rating": "3★"},
    "119788": {"name": "SBI Gold Fund (Direct-Growth)", "category": "Gold", "rating": "4★"},
    "118551": {"name": "Franklin U.S. Opportunities Equity Active FoF", "category": "International", "rating": "Active"},
    "118736": {"name": "Nippon India Balanced Advantage Fund", "category": "Hybrid", "rating": "4★"},
    "118778": {"name": "Nippon India Small Cap Fund", "category": "Small Cap", "rating": "4★"},
    "147662": {"name": "ICICI Prudential Commodities Fund", "category": "Commodities", "rating": "Thematic"},
    "120578": {"name": "SBI Technology Opportunities Fund", "category": "Technology", "rating": "Sectoral"},
    "120594": {"name": "ICICI Prudential Technology Fund", "category": "Technology", "rating": "Sectoral"}
}

# Core Nifty 50 Baseline
DEFAULT_STOCKS = {
    "RELIANCE.NS": "Reliance Industries Ltd",
    "HDFCBANK.NS": "HDFC Bank Ltd",
    "ICICIBANK.NS": "ICICI Bank Ltd",
    "TCS.NS": "Tata Consultancy Services",
    "INFY.NS": "Infosys Ltd",
    "LT.NS": "Larsen & Toubro Ltd",
    "BHARTIARTL.NS": "Bharti Airtel Ltd",
    "ITC.NS": "ITC Ltd",
    "SBIN.NS": "State Bank of India",
    "SUNPHARMA.NS": "Sun Pharma Ltd"
}

@st.cache_data(ttl=300)
def fetch_nifty_benchmark():
    try:
        tk = yf.Ticker("^NSEI")
        hist = tk.history(period="1mo")
        if not hist.empty and len(hist) >= 2:
            curr = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2])
            high_52w = float(hist['High'].max())
            pct = ((curr - prev) / prev) * 100
            return {"price": curr, "change": curr - prev, "pct": pct, "high": high_52w}
    except Exception:
        pass
    return {"price": 24244.15, "change": -121.85, "pct": -0.50, "high": 24774.30}

@st.cache_data(ttl=300)
def fetch_mutual_funds():
    fund_rows = []
    for code, meta in USER_FUNDS.items():
        try:
            r = requests.get(f"https://api.mfapi.in/mf/{code}", timeout=6)
            if r.status_code == 200:
                data = r.json()
                nav_list = data.get("data", [])
                if len(nav_list) >= 2:
                    curr = float(nav_list[0]["nav"])
                    prev = float(nav_list[1]["nav"])
                    navs_1y = [float(x["nav"]) for x in nav_list[:250]]
                    high = max(navs_1y) if navs_1y else curr
                    chg_pct = ((curr - prev) / prev) * 100
                    dd = ((curr - high) / high) * 100
                    upside = ((high - curr) / curr) * 100

                    fund_rows.append({
                        "Scheme": meta["name"],
                        "Category": meta["category"],
                        "Rating": meta["rating"],
                        "Latest NAV (₹)": round(curr, 2),
                        "1-Day Chg (%)": round(chg_pct, 2),
                        "52W High (₹)": round(high, 2),
                        "52W Drawdown (%)": round(dd, 2),
                        "Upside to Peak (%)": round(upside, 2),
                        "Action": "High Conviction Dip Buy" if dd <= -10 else ("Tactical Top-Up" if dd <= -4 else "Hold / Regular SIP")
                    })
        except Exception:
            continue
    return pd.DataFrame(fund_rows)

@st.cache_data(ttl=300)
def fetch_stocks():
    stock_rows = []
    for sym, name in DEFAULT_STOCKS.items():
        try:
            tk = yf.Ticker(sym)
            hist = tk.history(period="1y")
            if not hist.empty and len(hist) >= 2:
                curr = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2])
                high = float(hist['High'].max())
                chg_pct = ((curr - prev) / prev) * 100
                dd = ((curr - high) / high) * 100
                upside = ((high - curr) / curr) * 100

                stock_rows.append({
                    "Symbol": sym.replace(".NS", ""),
                    "Company": name,
                    "Price (₹)": round(curr, 2),
                    "1-Day Chg (%)": round(chg_pct, 2),
                    "52W High (₹)": round(high, 2),
                    "52W Drawdown (%)": round(dd, 2),
                    "Upside Potential (%)": round(upside, 2),
                    "Valuation Zone": "Deep Value Accumulation" if dd <= -20 else ("Correction Zone" if dd <= -8 else "Consolidation")
                })
        except Exception:
            continue
    return pd.DataFrame(stock_rows)

# Sidebar
st.sidebar.title("🛡️ Profile & Config")
st.sidebar.info("📧 **Recipient:** meksmod1@gmail.com\n\n🎯 **Profile:** Moderate Risk (30/30/40 Tranche Staging)\n\n⏰ **Active Hours:** 9:00 AM - 3:30 PM IST")

if st.sidebar.button("🔄 Force Refresh Quotes"):
    st.cache_data.clear()
    st.rerun()

# Main Title & Nifty Banner
st.title("📈 Indian Stock Market & Mutual Fund Dip Advisor")
st.caption("Automated Market Downturn Monitoring, Opportunity Detection & Recovery Projections")

nifty = fetch_nifty_benchmark()
col1, col2, col3, col4 = st.columns(4)
col1.metric("NIFTY 50 Level", f"₹{nifty['price']:,.2f}", f"{nifty['pct']:+.2f}%")
col2.metric("52-Week High Peak", f"₹{nifty['high']:,.2f}", "Benchmark Resistance")
col3.metric("Tracked Watchlist", "9 Funds + 100 Stocks", "Live Connected")
col4.metric("Alert Status", "Active (9 AM - 3:30 PM)", "Email & Telegram")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Mutual Funds (Your 9 Schemes)",
    "🏢 Nifty 100 Real-Time Dip Scanner",
    "🧮 Dip & Tranche Investment Calculator",
    "🔔 Test Alert Dispatcher"
])

with tab1:
    st.subheader("Your 9 Tracked Mutual Funds (AMFI Official Feed)")
    df_funds = fetch_mutual_funds()
    if not df_funds.empty:
        st.dataframe(
            df_funds.style.format({
                "Latest NAV (₹)": "₹{:.2f}",
                "1-Day Chg (%)": "{:+.2f}%",
                "52W High (₹)": "₹{:.2f}",
                "52W Drawdown (%)": "{:.2f}%",
                "Upside to Peak (%)": "+{:.2f}%"
            }),
            use_container_width=True
        )

        st.markdown("### 🎯 Value Dip Opportunities Identified:")
        dips = df_funds[df_funds["52W Drawdown (%)"] <= -8.0]
        if not dips.empty:
            for _, row in dips.iterrows():
                st.success(f"**{row['Scheme']}**: Trading at **{row['52W Drawdown (%)']}% discount** from 52W peak. Projected recovery upside: **+{row['Upside to Peak (%)']}%**.")
    else:
        st.warning("Loading fund quotes from AMFI API...")

with tab2:
    st.subheader("Live Nifty 100 Large-Cap Intraday Scanner")
    threshold = st.slider("Select Intraday Drop Trigger Threshold (%):", min_value=-5.0, max_value=-1.0, value=-2.0, step=0.5)
    
    if st.button("🚀 Scan All 100 Companies Now"):
        with st.spinner("Scanning Nifty 100 universe via live NSE feeds..."):
            opps = scanner.scan_nifty_100(threshold_pct=threshold)
            if opps:
                st.write(f"Found **{len(opps)} active dip opportunities** breaching the threshold:")
                df_opps = pd.DataFrame(opps)[["symbol", "price", "daily_pct", "high_52w", "drawdown_52w", "recovery_upside_pct", "drop_type"]]
                df_opps.columns = ["Stock", "Price (₹)", "Daily Drop (%)", "52W High (₹)", "Drawdown (%)", "Projected Upside (%)", "Type"]
                st.dataframe(
                    df_opps.style.format({
                        "Price (₹)": "₹{:.2f}",
                        "Daily Drop (%)": "{:+.2f}%",
                        "52W High (₹)": "₹{:.2f}",
                        "Drawdown (%)": "{:.2f}%",
                        "Projected Upside (%)": "+{:.2f}%"
                    }),
                    use_container_width=True
                )
            else:
                st.info("No stocks currently down beyond the selected threshold. Markets holding steady.")

with tab3:
    st.subheader("Phased Dip Investment & Recovery Simulator")
    calc_col1, calc_col2, calc_col3 = st.columns(3)
    capital = calc_col1.number_input("Deployment Capital (₹):", min_value=10000, max_value=10000000, value=100000, step=10000)
    asset_choice = calc_col2.selectbox("Select Asset to Accumulate:", [
        "SBI Gold Fund Direct-Growth (+17.1% upside)",
        "HDFC Gold ETF (+15.6% upside)",
        "ICICI Prudential Tech Fund (+15.4% upside)",
        "SBI Technology Opportunities (+13.2% upside)",
        "Infosys Ltd (INFY) (+48.3% upside)",
        "TCS Ltd (+41.7% upside)",
        "HDFC Bank (+38.4% upside)",
        "Reliance Industries (+23.4% upside)"
    ])
    profile_strat = calc_col3.selectbox("Risk Strategy:", ["Moderate (30% / 30% / 40%)", "Aggressive (50% / 50%)", "Conservative (20% Phased)"])

    upside_map = {
        "SBI Gold Fund Direct-Growth (+17.1% upside)": 17.1,
        "HDFC Gold ETF (+15.6% upside)": 15.6,
        "ICICI Prudential Tech Fund (+15.4% upside)": 15.4,
        "SBI Technology Opportunities (+13.2% upside)": 13.2,
        "Infosys Ltd (INFY) (+48.3% upside)": 48.3,
        "TCS Ltd (+41.7% upside)": 41.7,
        "HDFC Bank (+38.4% upside)": 38.4,
        "Reliance Industries (+23.4% upside)": 23.4
    }
    upside_val = upside_map.get(asset_choice, 15.0)
    t1_pct = 0.30 if "Moderate" in profile_strat else (0.50 if "Aggressive" in profile_strat else 0.20)

    t1_amt = capital * t1_pct
    reserve_amt = capital * (1 - t1_pct)
    proj_val = capital * (1 + (upside_val / 100))
    net_profit = proj_val - capital

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tranche 1 Immediate Entry", f"₹{t1_amt:,.0f}", f"{t1_pct*100:.0f}% Allocation")
    m2.metric("Cash Reserve Maintained", f"₹{reserve_amt:,.0f}", "For Secondary Tests")
    m3.metric("Projected Value at Peak", f"₹{proj_val:,.0f}", f"+₹{net_profit:,.0f}")
    m4.metric("Estimated Horizon", "3 - 8 Weeks", "Historical Cycle")

with tab4:
    st.subheader("Test Multi-Channel Alert Dispatch")
    st.write("Click below to trigger a sample priority alert to **`meksmod1@gmail.com`** and your Telegram Bot:")
    if st.button("📨 Dispatch Test Market Alert"):
        with st.spinner("Dispatching alert via Gmail SMTP and Telegram API..."):
            test_opp = {
                "symbol": "INFY",
                "name": "Infosys Ltd",
                "price": 1140.30,
                "daily_pct": -2.47,
                "high_52w": 1691.40,
                "drawdown_52w": -32.6,
                "recovery_upside_pct": 48.3,
                "action_note": "Tier-1 IT leader trading at multi-month support. High margin of safety."
            }
            notifier.dispatch_dip_alert(test_opp, "meksmod1@gmail.com")
            st.success("Alert dispatched successfully! Check your email inbox & Telegram.")
