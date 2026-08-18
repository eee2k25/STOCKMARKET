# streamlit_app.py - Fixed & Working Version
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests
from config import AppConfig
from styles import load_custom_css
import pytz

# Page Configuration
st.set_page_config(
    page_title=f"{AppConfig.APP_NAME} v{AppConfig.VERSION}",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Custom Styles
load_custom_css()

# Initialize Session State
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = []
if 'alerts' not in st.session_state:
    st.session_state.alerts = []

# ==================== UTILITY FUNCTIONS ====================

class MarketUtils:
    """Market utility functions"""
    
    @staticmethod
    def is_market_open():
        """Check if Indian market is currently open"""
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        
        if now.weekday() >= 5:
            return False
        
        market_open = now.replace(hour=9, minute=15, second=0)
        market_close = now.replace(hour=15, minute=30, second=0)
        
        return market_open <= now <= market_close
    
    @staticmethod
    def get_market_status():
        """Get current market status"""
        is_open = MarketUtils.is_market_open()
        if is_open:
            return '<span class="status-live"></span> Market LIVE', True
        else:
            return '<span class="status-closed"></span> Market Closed', False
    
    @staticmethod
    def format_inr(value):
        """Format number in Indian numbering system"""
        if value >= 10000000:
            return f"₹{value/10000000:.2f} Cr"
        elif value >= 100000:
            return f"₹{value/100000:.2f} L"
        else:
            return f"₹{value:,.2f}"

class IndianMarketData:
    """Fetch Indian market data"""
    
    @staticmethod
    @st.cache_data(ttl=300)
    def get_mutual_fund_nav(amfi_code):
        """Fetch NAV from AMFI"""
        try:
            url = f"https://api.mfapi.in/mf/{amfi_code}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    'nav': float(data['data'][0]['nav']),
                    'date': data['data'][0]['date'],
                    'scheme_name': data['meta']['scheme_name']
                }
            return None
        except Exception as e:
            return None
    
    @staticmethod
    @st.cache_data(ttl=60)
    def get_stock_data(symbol, period='1mo'):
        """Fetch stock data with caching"""
        try:
            stock = yf.Ticker(symbol)
            df = stock.history(period=period)
            info = stock.info
            return df, info
        except Exception as e:
            return None, None

class TechnicalIndicators:
    """Simple technical indicators"""
    
    @staticmethod
    def calculate_sma(data, window):
        """Simple Moving Average"""
        return data.rolling(window=window).mean()
    
    @staticmethod
    def calculate_rsi(data, window=14):
        """Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_bollinger_bands(data, window=20, num_std=2):
        """Bollinger Bands"""
        sma = data.rolling(window=window).mean()
        std = data.rolling(window=window).std()
        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)
        return upper_band, sma, lower_band

# ==================== HEADER ====================

def render_header():
    """Render app header"""
    st.markdown(f"""
        <div class="app-header">
            <h1 class="app-title">📊 {AppConfig.APP_NAME}</h1>
            <p class="app-subtitle">Indian Markets • Mutual Funds • Real-time Alerts</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    status_text, is_open = MarketUtils.get_market_status()
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Market Status</div>
                <div class="metric-value" style="font-size: 1.2rem;">{status_text}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">IST Time</div>
                <div class="metric-value" style="font-size: 1.2rem;">{now.strftime('%I:%M %p')}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        nifty_data, _ = IndianMarketData.get_stock_data('^NSEI', '1d')
        if nifty_data is not None and len(nifty_data) > 0:
            nifty_price = nifty_data['Close'].iloc[-1]
            nifty_change = ((nifty_data['Close'].iloc[-1] - nifty_data['Open'].iloc[-1]) / nifty_data['Open'].iloc[-1]) * 100
            change_color = '#4ade80' if nifty_change >= 0 else '#f87171'
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">NIFTY 50</div>
                    <div class="metric-value" style="font-size: 1.2rem;">{nifty_price:.2f}</div>
                    <div style="color: {change_color}; font-weight: 600;">{nifty_change:+.2f}%</div>
                </div>
            """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Active Alerts</div>
                <div class="metric-value">{len(st.session_state.alerts)}</div>
            </div>
        """, unsafe_allow_html=True)

# ==================== SIDEBAR ====================

def render_sidebar():
    """Render sidebar navigation"""
    with st.sidebar:
        st.markdown("### 🧭 Navigation")
        
        page = st.radio(
            "Select Page",
            [
                "🏠 Dashboard",
                "🇮🇳 Indian Markets",
                "💎 Mutual Funds",
                "📊 Stock Scanner",
                "💼 Portfolio",
                "🔔 Alerts",
                "⚙️ Settings"
            ],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        st.markdown("### ⚡ Quick Actions")
        
        if st.button("🔄 Refresh Data", key="refresh_btn"):
            st.cache_data.clear()
            st.success("✅ Data Refreshed!")
            st.rerun()
        
        st.markdown("---")
        
        st.caption(f"v{AppConfig.VERSION}")
        st.caption(f"By {AppConfig.AUTHOR}")
        
        return page

# ==================== PAGES ====================

def render_dashboard():
    """Main dashboard"""
    st.title("🏠 Market Dashboard")
    
    st.subheader("💰 Your Mutual Funds")
    
    mf_data = []
    for fund in AppConfig.TRACKED_MUTUAL_FUNDS:
        nav_data = IndianMarketData.get_mutual_fund_nav(fund['amfi'])
        if nav_data:
            mf_data.append({
                'Fund Name': fund['name'][:40] + '...',
                'Category': fund['category'],
                'NAV': f"₹{nav_data['nav']:.2f}",
                'Rating': '⭐' * fund['rating'],
                'Updated': nav_data['date']
            })
    
    if mf_data:
        df = pd.DataFrame(mf_data)
        st.dataframe(df, hide_index=True)
    else:
        st.warning("Unable to fetch mutual fund data. Please try again.")
    
    st.markdown("---")
    
    st.subheader("🔔 Recent Alerts")
    
    if st.session_state.alerts:
        for alert in st.session_state.alerts[-5:]:
            st.markdown(f"""
                <div class="alert-info">
                    <strong>{alert.get('symbol', 'N/A')}</strong>: {alert.get('message', 'No message')}
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No recent alerts")

def render_indian_markets():
    """Indian markets view"""
    st.title("🇮🇳 Indian Markets")
    
    st.subheader("📊 NIFTY 50 Performance")
    
    df, info = IndianMarketData.get_stock_data('^NSEI', '1mo')
    
    if df is not None and len(df) > 0:
        df['SMA_20'] = TechnicalIndicators.calculate_sma(df['Close'], 20)
        df['SMA_50'] = TechnicalIndicators.calculate_sma(df['Close'], 50)
        df['RSI'] = TechnicalIndicators.calculate_rsi(df['Close'])
        df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = TechnicalIndicators.calculate_bollinger_bands(df['Close'])
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=('NIFTY 50 Price', 'RSI'),
            row_heights=[0.7, 0.3]
        )
        
        # FIXED: Properly closed parenthesis
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name='NIFTY 50'
            ), 
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['SMA_20'],
                name='SMA 20',
                line=dict(color='orange', width=1)
            ), 
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['SMA_50'],
                name='SMA 50',
                line=dict(color='blue', width=1)
            ), 
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['BB_Upper'],
                name='BB Upper',
                line=dict(color='gray', width=1, dash='dash')
            ), 
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['BB_Lower'],
                name='BB Lower',
                line=dict(color='gray', width=1, dash='dash'),
                fill='tonexty'
            ), 
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df['RSI'],
                name='RSI',
                line=dict(color='purple', width=2)
            ), 
            row=2, col=1
        )
        
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        fig.update_layout(
            height=700,
            template='plotly_dark',
            xaxis_rangeslider_visible=False
        )
        
        st.plotly_chart(fig)
        
        col1, col2, col3, col4 = st.columns(4)
        
        current_price = df['Close'].iloc[-1]
        day_high = df['High'].iloc[-1]
        day_low = df['Low'].iloc[-1]
        rsi_value = df['RSI'].iloc[-1]
        
        with col1:
            st.metric("Current", f"{current_price:.2f}")
        with col2:
            st.metric("Day High", f"{day_high:.2f}")
        with col3:
            st.metric("Day Low", f"{day_low:.2f}")
        with col4:
            st.metric("RSI", f"{rsi_value:.2f}")

def render_mutual_funds():
    """Detailed mutual funds view"""
    st.title("💎 Mutual Funds Analysis")
    
    for fund in AppConfig.TRACKED_MUTUAL_FUNDS:
        with st.expander(f"📁 {fund['name']}"):
            nav_data = IndianMarketData.get_mutual_fund_nav(fund['amfi'])
            
            if nav_data:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Current NAV", f"₹{nav_data['nav']:.2f}")
                with col2:
                    st.metric("Category", fund['category'])
                with col3:
                    st.metric("Rating", '⭐' * fund['rating'])
                
                st.caption(f"Last Updated: {nav_data['date']}")
            else:
                st.warning("Unable to fetch data")

def render_stock_scanner():
    """Stock scanner"""
    st.title("📊 Stock Scanner")
    
    st.subheader("🔍 Nifty 100 Scanner")
    
    col1, col2 = st.columns(2)
    
    with col1:
        min_drop = st.slider("Minimum Drop %", 0.0, 10.0, 2.0, 0.5)
    with col2:
        sort_by = st.selectbox("Sort By", ["Drop %", "Volume", "Price"])
    
    if st.button("🚀 Scan Now", key="scan_btn"):
        with st.spinner("Scanning stocks..."):
            scan_results = []
            
            for symbol in AppConfig.NIFTY_100_STOCKS[:10]:
                df, info = IndianMarketData.get_stock_data(symbol, '1d')
                
                if df is not None and len(df) > 0:
                    current_price = df['Close'].iloc[-1]
                    open_price = df['Open'].iloc[-1]
                    change_pct = ((current_price - open_price) / open_price) * 100
                    
                    if change_pct <= -min_drop:
                        scan_results.append({
                            'Symbol': symbol.replace('.NS', ''),
                            'Price': f"₹{current_price:.2f}",
                            'Change %': f"{change_pct:.2f}%",
                            'Volume': f"{df['Volume'].iloc[-1]/1e6:.2f}M"
                        })
            
            if scan_results:
                st.success(f"✅ Found {len(scan_results)} opportunities!")
                st.dataframe(pd.DataFrame(scan_results), hide_index=True)
            else:
                st.info("No stocks matching criteria found")

def render_portfolio():
    """Portfolio tracker"""
    st.title("💼 Portfolio Tracker")
    
    tab1, tab2 = st.tabs(["📊 Holdings", "➕ Add Stock"])
    
    with tab1:
        if st.session_state.portfolio:
            portfolio_df = pd.DataFrame(st.session_state.portfolio)
            st.dataframe(portfolio_df, hide_index=True)
        else:
            st.info("Your portfolio is empty. Add stocks from the 'Add Stock' tab.")
    
    with tab2:
        st.subheader("Add New Stock")
        
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.text_input("Stock Symbol (e.g., RELIANCE.NS)")
            shares = st.number_input("Number of Shares", 1, 10000, 10)
        
        with col2:
            buy_price = st.number_input("Buy Price (₹)", 1.0, 100000.0, 100.0)
            buy_date = st.date_input("Purchase Date")
        
        if st.button("➕ Add to Portfolio", key="add_portfolio_btn"):
            st.session_state.portfolio.append({
                
