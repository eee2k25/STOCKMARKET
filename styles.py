# styles.py - Cream · Gold · Red glassmorphism UI styling for the Streamlit app.
# Kept API-compatible: load_custom_css() injects the design system below.

import streamlit as st

# Design tokens (mirror interactive_portfolio_app.html)
PALETTE = {
    "bg": "#f6efe0",             # cream canvas
    "glass": "rgba(255, 252, 242, 0.62)",
    "glass_grad": "linear-gradient(150deg, rgba(255,253,246,0.78), rgba(252,244,226,0.52))",
    "border": "rgba(146, 110, 32, 0.16)",
    "border_strong": "rgba(146, 110, 32, 0.32)",
    "text1": "#33261a",          # espresso
    "text2": "#75634c",
    "text3": "#a08d70",
    "gold": "#c9a227",
    "gold_deep": "#9a6d00",
    "gold_ink": "#8a6d1f",
    "gold_tint": "rgba(212, 175, 55, 0.20)",
    "red": "#b03a2e",
    "red_tint": "rgba(176, 58, 46, 0.12)",
    "warn": "#b9770e",
    "warn_tint": "rgba(185, 119, 14, 0.14)",
    "info": "#7a5c2e",
    "info_tint": "rgba(122, 92, 46, 0.12)",
    "shadow_rest": ("inset 0 1px 0 rgba(255,255,255,0.75), 0 2px 6px -2px rgba(92,64,14,0.14), "
                    "0 10px 26px -16px rgba(92,64,14,0.28)"),
    "shadow_lift": ("inset 0 1px 0 rgba(255,255,255,0.85), 0 4px 10px -4px rgba(92,64,14,0.20), "
                    "0 22px 44px -18px rgba(92,64,14,0.42)"),
}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Fraunces:opsz,wght@9..144,600;9..144,700;9..144,800&display=swap');

/* ============ Base — cream canvas with gold/red blooms ============ */
html, body, [class*="css"], .stApp, .main {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: {PALETTE["text1"]};
}}

.stApp {{
    background-color: {PALETTE["bg"]};
    background-image:
        radial-gradient(1000px 480px at 12% -8%, rgba(201,162,39,0.18), transparent 58%),
        radial-gradient(900px 460px at 96% 12%, rgba(176,58,46,0.10), transparent 55%),
        radial-gradient(1100px 520px at 55% 118%, rgba(201,162,39,0.18), transparent 60%);
    background-attachment: fixed;
}}

h1, h2, h3 {{ letter-spacing: -0.01em; color: {PALETTE["text1"]}; }}
h1, h2 {{ font-family: 'Fraunces', Georgia, serif; font-weight: 700; }}
p, li, label {{ color: {PALETTE["text2"]}; }}

::selection {{ background: rgba(212, 175, 55, 0.38); }}

/* ============ Header — frosted cream glass ============ */
.app-header {{
    background: {PALETTE["glass_grad"]};
    backdrop-filter: blur(18px) saturate(1.4);
    -webkit-backdrop-filter: blur(18px) saturate(1.4);
    border: 1px solid {PALETTE["border"]};
    border-radius: 16px;
    padding: 1.6rem 1.8rem;
    margin-bottom: 1.4rem;
    box-shadow: {PALETTE["shadow_rest"]};
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
.app-header:hover {{
    box-shadow: {PALETTE["shadow_lift"]};
    border-color: {PALETTE["gold"]};
}}
.app-header::before {{
    content: "";
    position: absolute; inset: 0;
    background: radial-gradient(480px 180px at 90% -30%, rgba(212,175,55,0.22), transparent 65%);
    pointer-events: none;
}}
.app-title {{
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: {PALETTE["text1"]};
    margin: 0;
    letter-spacing: -0.015em;
    position: relative;
}}
.app-subtitle {{
    font-size: 0.85rem;
    color: {PALETTE["text2"]};
    margin-top: 0.35rem;
    position: relative;
}}
.app-subtitle .sep {{
    margin: 0 0.5rem;
    color: {PALETTE["text3"]};
}}

/* ============ Metric cards — glass, lift on hover ============ */
.metric-card {{
    background: {PALETTE["glass_grad"]};
    backdrop-filter: blur(16px) saturate(1.35);
    -webkit-backdrop-filter: blur(16px) saturate(1.35);
    border: 1px solid {PALETTE["border"]};
    border-radius: 12px;
    padding: 1rem 1.1rem;
    box-shadow: {PALETTE["shadow_rest"]};
    margin: 0.25rem 0 0.75rem;
    transition: transform 0.2s cubic-bezier(0.22, 0.9, 0.32, 1.2), box-shadow 0.2s ease, border-color 0.2s ease;
}}
.metric-card:hover {{
    transform: translateY(-3px);
    border-color: {PALETTE["gold"]};
    box-shadow: {PALETTE["shadow_lift"]};
}}
.metric-label {{
    font-size: 0.65rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {PALETTE["text3"]};
    margin-bottom: 0.3rem;
}}
.metric-value {{
    font-size: 1.45rem;
    font-weight: 800;
    color: {PALETTE["text1"]};
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.01em;
    line-height: 1.2;
}}
.metric-value.positive {{ color: {PALETTE["gold_deep"]}; }}
.metric-value.negative {{ color: {PALETTE["red"]}; }}
.metric-value.neutral {{ color: {PALETTE["text1"]}; }}
.metric-value.mono {{ font-family: 'JetBrains Mono', monospace; }}

/* ============ Alerts — tinted gold/red glass ============ */
.alert-box {{
    display: flex; align-items: flex-start; gap: 0.7rem;
    padding: 0.8rem 1rem;
    border-radius: 10px;
    margin: 0.4rem 0;
    font-size: 0.9rem;
    border: 1px solid;
    color: {PALETTE["text1"]};
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    box-shadow: {PALETTE["shadow_rest"]};
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
.alert-box:hover {{ transform: translateY(-2px); }}
.alert-box::before {{
    content: "";
    width: 7px; height: 7px; border-radius: 50%;
    background: currentColor; flex: none; margin-top: 0.45rem;
}}
.alert-success {{ background: {PALETTE["gold_tint"]}; border-color: rgba(185,119,14,0.4); }}
.alert-warning {{ background: {PALETTE["warn_tint"]}; border-color: rgba(185,119,14,0.4); }}
.alert-danger  {{ background: {PALETTE["red_tint"]}; border-color: rgba(176,58,46,0.38); }}
.alert-info    {{ background: {PALETTE["info_tint"]}; border-color: rgba(122,92,46,0.35); }}

/* Legacy class names kept working */
.alert-success strong, .alert-warning strong, .alert-danger strong, .alert-info strong {{ color: inherit; }}

/* ============ Buttons — glass with gold primary; rise on hover ============ */
.stButton > button {{
    background: {PALETTE["glass_grad"]};
    backdrop-filter: blur(14px) saturate(1.3);
    -webkit-backdrop-filter: blur(14px) saturate(1.3);
    color: {PALETTE["text1"]};
    border: 1px solid {PALETTE["border_strong"]};
    padding: 0.5rem 1.2rem;
    border-radius: 9px;
    font-weight: 700;
    font-size: 0.88rem;
    box-shadow: {PALETTE["shadow_rest"]};
    transition: all 0.2s cubic-bezier(0.22, 0.9, 0.32, 1.2);
}}
.stButton > button:hover {{
    background: linear-gradient(150deg, rgba(255,253,246,0.92), rgba(252,244,226,0.7));
    border-color: {PALETTE["gold"]};
    transform: translateY(-3px);
    box-shadow: {PALETTE["shadow_lift"]};
    color: {PALETTE["text1"]};
}}
.stButton > button:active {{
    transform: translateY(-1px);
    box-shadow: inset 0 2px 4px rgba(92,64,14,0.15);
}}
.stButton > button[kind="primary"], .stButton > button[data-testid="stFormSubmitButton"] {{
    background: linear-gradient(140deg, #e8c96a 0%, #c9a227 55%, #b8860b 100%);
    border-color: rgba(154, 109, 0, 0.55);
    color: #3a2c05;
    font-weight: 800;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.55), 0 6px 18px -8px rgba(154,109,0,0.65);
}}
.stButton > button[kind="primary"]:hover {{
    background: linear-gradient(140deg, #f1d987 0%, #d4af37 55%, #c9a227 100%);
    color: #3a2c05;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 12px 30px -10px rgba(154,109,0,0.75);
}}

/* ============ Sidebar — cream glass ============ */
section[data-testid="stSidebar"] {{
    background: rgba(248, 242, 228, 0.72);
    backdrop-filter: blur(16px) saturate(1.3);
    -webkit-backdrop-filter: blur(16px) saturate(1.3);
    border-right: 1px solid {PALETTE["border"]};
}}
section[data-testid="stSidebar"] .block-container {{ padding-top: 1.5rem; }}

/* ============ Widgets ============ */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {PALETTE["border"]}; }}
.stTabs [data-baseweb="tab"] {{
    background-color: transparent;
    border-radius: 9px 9px 0 0;
    padding: 0.5rem 1rem;
    color: {PALETTE["text2"]};
    font-weight: 700;
    transition: all 0.18s ease;
}}
.stTabs [data-baseweb="tab"]:hover {{ transform: translateY(-2px); color: {PALETTE["text1"]}; }}
.stTabs [aria-selected="true"] {{
    background: linear-gradient(150deg, rgba(255,255,255,0.95), rgba(253,246,228,0.8));
    color: {PALETTE["gold_deep"]} !important;
    box-shadow: 0 10px 22px -12px rgba(154,109,0,0.55);
    transform: translateY(-2px);
}}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: {PALETTE["gold"]}; }}

div[data-testid="stExpander"] {{
    background: {PALETTE["glass_grad"]};
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid {PALETTE["border"]};
    border-radius: 12px;
    box-shadow: {PALETTE["shadow_rest"]};
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
div[data-testid="stExpander"]:hover {{ border-color: {PALETTE["gold"]}; box-shadow: {PALETTE["shadow_lift"]}; }}

div[data-testid="stMetric"] {{
    background: {PALETTE["glass_grad"]};
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid {PALETTE["border"]};
    border-radius: 12px;
    box-shadow: {PALETTE["shadow_rest"]};
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
div[data-testid="stMetric"]:hover {{ transform: translateY(-3px); border-color: {PALETTE["gold"]}; box-shadow: {PALETTE["shadow_lift"]}; }}
div[data-testid="stMetricLabel"] p {{ font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase; color: {PALETTE["text3"]}; font-weight: 800; }}
div[data-testid="stMetricValue"] {{ font-weight: 800; font-variant-numeric: tabular-nums; color: {PALETTE["text1"]}; }}

/* Dataframe / tables */
[data-testid="stDataFrame"] {{ border: 1px solid {PALETTE["border"]}; border-radius: 12px; overflow: hidden; }}
table {{ border-color: {PALETTE["border"]} !important; }}
thead tr {{ background: rgba(250, 240, 216, 0.95) !important; }}
th {{ color: {PALETTE["text3"]} !important; text-transform: uppercase; font-size: 0.68rem !important; letter-spacing: 0.08em; }}

/* Inputs */
.stTextInput > div > div > input, .stNumberInput input, .stSelectbox div > div > div {{
    background: {PALETTE["glass"]};
    border: 1px solid {PALETTE["border_strong"]};
    border-radius: 9px;
    color: {PALETTE["text1"]};
}}
.stTextInput > div > div > input:focus {{
    border-color: {PALETTE["gold"]};
    box-shadow: 0 0 0 3px rgba(212,175,55,0.22);
}}

/* ============ Status indicators ============ */
.status-live, .status-closed {{
    display: inline-block;
    width: 9px; height: 9px;
    border-radius: 50%;
    margin-right: 8px;
}}
.status-live {{
    background: {PALETTE["gold"]};
    animation: pulse 2s infinite;
}}
.status-closed {{ background: {PALETTE["text3"]}; }}

@keyframes pulse {{
    0%, 100% {{ box-shadow: 0 0 0 0 rgba(201,162,39,0.45); }}
    70% {{ box-shadow: 0 0 0 7px rgba(201,162,39,0); }}
}}
</style>
"""


def load_custom_css():
    """Load the custom design system CSS."""
    st.markdown(CSS, unsafe_allow_html=True)
