# streamlit_app.py — Streamlit front-end for MEK Stock Alert Pro.
# The Dashboard page embeds the exact same interactive cream/gold/red
# dashboard served by app.py (crosshair hover tooltips included), with the
# market snapshot injected directly — no backend needed.

import datetime

import pytz
import streamlit as st
import streamlit.components.v1 as components

from styles import load_custom_css
from market_data import collect_market_data, load_config
from dashboard_embed import build_embed_html
import nifty100_intraday_scanner as scanner

# Page Configuration
st.set_page_config(
    page_title="MEK Stock Alert Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load the shared cream · gold · red design system
load_custom_css()

if "scan_results" not in st.session_state:
    st.session_state.scan_results = None


# ==================== DATA ====================

@st.cache_data(ttl=300, show_spinner=False)
def cached_market_data():
    return collect_market_data()


def ist_now():
    return datetime.datetime.now(pytz.timezone("Asia/Kolkata"))


def market_open(now=None):
    now = now or ist_now()
    if now.weekday() >= 5:
        return False
    mins = now.hour * 60 + now.minute
    return 555 <= mins <= 930  # 09:15 - 15:30 IST


# ==================== SHARED CHROME ====================

def render_header():
    now = ist_now()
    open_ = market_open(now)
    status = (
        f'<span class="status-live"></span><b style="color:{PALETTE_OK}">Market LIVE</b>'
        if open_ else
        '<span class="status-closed"></span><b>Market Closed</b>'
    )
    st.markdown(f"""
        <div class="app-header">
            <h1 class="app-title">📈 MEK Stock Alert Pro</h1>
            <p class="app-subtitle">
                {status}<span class="sep">·</span>Indian Markets · Mutual Funds · Dip Alerts
                <span class="sep">·</span>{now.strftime('%d %b %Y, %I:%M %p')} IST
            </p>
        </div>
    """, unsafe_allow_html=True)


PALETTE_OK = "#9a6d00"  # gold = positive in this theme


def render_sidebar():
    with st.sidebar:
        st.markdown("### 🧭 Navigate")
        page = st.radio(
            "Page",
            ["🏠 Dashboard", "🔍 NIFTY 100 Scanner", "📧 Email Digest Preview", "ℹ️ About & Setup"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.markdown("### ⚡ Quick actions")
        if st.button("🔄 Refresh data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.markdown("---")
        cfg = load_config()
        st.caption(f"Risk profile: **{cfg.get('risk_profile', 'moderate').title()}**")
        st.caption(f"Alerts → {cfg.get('email', 'not configured')}")
        st.caption("v2.0 · Cream · Gold · Red")
        return page


# ==================== PAGES ====================

def page_dashboard():
    with st.spinner("Fetching live AMFI NAVs & NSE quotes…"):
        data = cached_market_data()
    components.html(build_embed_html(data), height=2100, scrolling=True)


def page_scanner():
    st.markdown("#### 🔍 Intraday Flash Scanner")
    st.caption("Screens all NIFTY 100 constituents for sudden dips ≥ 2%, sharp intraday pullbacks and deep value zones.")

    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        if st.button("🚀 Run Scan", use_container_width=True, type="primary"):
            with st.spinner("Crunching 5-day price action for all 100 constituents…"):
                st.session_state.scan_results = scanner.scan_nifty_100(threshold_pct=-2.0)

    opps = st.session_state.scan_results
    if opps is None:
        st.info("Run the scanner to surface every NIFTY 100 leader currently in a dip.")
        return

    m1, m2, m3 = st.columns(3)
    m1.markdown('<div class="metric-card"><div class="metric-label">Opportunities</div>'
                f'<div class="metric-value">{len(opps)}</div></div>', unsafe_allow_html=True)
    if opps:
        deep = [o for o in opps if o["drawdown_52w"] <= -20]
        flash = [o for o in opps if o["daily_pct"] <= -2]
        m2.markdown('<div class="metric-card"><div class="metric-label">Deep value zone</div>'
                    f'<div class="metric-value negative">{len(deep)}</div>'
                    '<div class="metric-label" style="margin-top:4px">down &gt; 20% from peak</div></div>', unsafe_allow_html=True)
        m3.markdown('<div class="metric-card"><div class="metric-label">Flash dips today</div>'
                    f'<div class="metric-value positive">{len(flash)}</div>'
                    '<div class="metric-label" style="margin-top:4px">down ≥ 2% on the day</div></div>', unsafe_allow_html=True)

        rows = [{
            "Symbol": o["symbol"], "Price (₹)": o["price"], "Day %": o["daily_pct"],
            "52w High (₹)": o["high_52w"], "From Peak %": o["drawdown_52w"],
            "Recovery %": o["recovery_upside_pct"], "Signal": o["drop_type"],
        } for o in opps]
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.success("Clean tape — no NIFTY 100 leader is in a sharp dip right now. Discipline beats FOMO.")


def page_email_preview():
    st.markdown("#### 📧 Daily Digest Email Preview")
    st.caption("Exactly what the automated 4:00 PM IST email delivers to your inbox (GitHub Actions or `python send_email.py`).")

    if st.button("Generate preview", use_container_width=True, type="primary"):
        with st.spinner("Building the advisory report…"):
            import indian_market_monitor as imm
            from generate_preview import build_html_report
            rep = imm.generate_advisory_report(risk_tolerance="moderate", user_email=load_config().get("email", ""))
            st.session_state["email_html"] = build_html_report(rep)

    html = st.session_state.get("email_html")
    if html:
        components.html(html, height=2500, scrolling=True)
    else:
        st.info("Click **Generate preview** to render the latest digest.")


def page_about():
    st.markdown("#### ℹ️ About & Setup")
    st.markdown(
        """
This project ships **two front-ends over one shared engine**:

| | Web dashboard (`app.py`) | This Streamlit app |
|---|---|---|
| Run | `python app.py` → `http://localhost:5000` | `streamlit run streamlit_app.py` |
| Best for | Full experience — live scanner, test alerts, auto-refresh | Quick hosted view (Streamlit Cloud) |
| Dashboard | Served directly | Same UI, embedded with a data snapshot |

**Design system** — cream canvas, gold = gains, red = losses, frosted-glass
panels, and controls that rise off the page on hover/press. Charts have
crosshair hover: value at that point + rise/fall to the latest.

**Data sources** — AMFI NAV feed (api.mfapi.in) and Yahoo Finance (NSE).
If the feeds are unreachable, a clearly-labelled sample snapshot keeps the
UI usable.

**Automated email alerts** — push to GitHub and set the
`SENDER_EMAIL` / `SENDER_APP_PASSWORD` secrets; the workflow emails the
digest at market open, midday and close on trading days.
        """
    )
    st.markdown("---")
    st.caption("Mutual fund investments are subject to market risks. Personal advisory tool — not investment advice.")


# ==================== MAIN ====================

def main():
    render_header()
    page = render_sidebar()

    if page == "🏠 Dashboard":
        page_dashboard()
    elif page == "🔍 NIFTY 100 Scanner":
        page_scanner()
    elif page == "📧 Email Digest Preview":
        page_email_preview()
    else:
        page_about()


if __name__ == "__main__":
    main()
