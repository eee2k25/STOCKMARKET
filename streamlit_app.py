# streamlit_app_v2.py - Complete Upgraded App
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
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

# Utility Functions
class MarketUtils:
    """Market utility functions"""
    
    @staticmethod
    def is_market_open():
        """Check if Indian market is currently open"""
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        
        # Check if weekday
        if now.weekday() >= 5:  # Saturday or Sunday
            return False
        
        # Check market hours
        market_open = now.replace(hour=9, minute=15, second=0)
        market_close = now.replace(hour=15, minute=30, second=0)
        
        return market_open <= now <= market_close
    
    @staticmethod
    def get_market_status():
        """Get current market status with emoji"""
        is_open = MarketUtils.is_market_open()
        if is_open:
            return '<span class="status-live"></span> Market LIVE', 'success'
        else:
            return '<span class="status-closed"></span> Market Closed', 'error'
    
    @staticmethod
    def format_inr(value):
        """Format number in Indian numbering system"""
        if value >= 10000000:  # 1 Crore
            return f"₹{value/10000000:.2f} Cr"
        elif value >= 100000:  # 1 Lakh
            return f"₹{value/100000:.2f} L"
        else:
            return f"₹{value:,.2f}"

class IndianMarketData:
    """Fetch Indian market data"""
    
    @staticmethod
    def get_nifty_100():
        """Get Nifty 100 constituents"""
        # You can maintain this list or fetch from NSE API
        nifty_100 = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
            "ICICIBANK.NS", "KOTAKBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS",
            # ... add all 100 stocks
        ]
        return nifty_100
    
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
            st.error(f"Error fetching MF data: {e}")
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
            st.error(f"Error fetching {symbol}: {e}")
            return None, None

class TechnicalAnalysis:
    """Advanced technical analysis"""
    
    @staticmethod
    def calculate_all_indicators(df):
        """Calculate comprehensive technical indicators"""
        # Moving Averages
        df['SMA_20'] = ta.sma(df['Close'], length=20)
        df['SMA_50'] = ta.sma(df['Close'], length=50)
        df['SMA_200'] = ta.sma(df['Close'], length=200)
        df['EMA_12'] = ta.ema(df['Close'], length=12)
        df['EMA_26'] = ta.ema(df['Close'], length=26)
        
        # Momentum Indicators
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['STOCH_K'] = ta.stoch(df['High'], df['Low'], df['Close'], k=14)['STOCHk_14_3_3']
        
        # MACD
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        
        # Bollinger Bands
        bbands = ta.bbands(df['Close'], length=20, std=2)
        df = pd.concat([df, bbands], axis=1)
        
        # Volume Indicators
        df['OBV'] = ta.obv(df['Close'], df['Volume'])
        df['VWAP'] = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume'])
        
        # Volatility
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        # Support/Resistance
        df['Pivot'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['R1'] = 2 * df['Pivot'] - df['Low']
        df['S1'] = 2 * df['Pivot'] - df['High']
        
        return df
    
    @staticmethod
    def generate_signals(df):
        """Generate trading signals"""
        signals = []
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # RSI Signals
        if latest['RSI'] < 30:
            signals.append({
                'type': 'BUY',
                'strength': 'STRONG',
                'indicator': 'RSI',
                'message': f"Oversold (RSI: {latest['RSI']:.2f})",
                'emoji': '🟢'
            })
        elif latest['RSI'] > 70:
            signals.append({
                'type': 'SELL',
                'strength': 'STRONG',
                'indicator': 'RSI',
                'message': f"Overbought (RSI: {latest['RSI']:.2f})",
                'emoji': '🔴'
            })
        
        # MACD Crossover
        if prev['MACD_12_26_9'] < prev['MACDs_12_26_9'] and latest['MACD_12_26_9'] > latest['MACDs_12_26_9']:
            signals.append({
                'type': 'BUY',
                'strength': 'MEDIUM',
                'indicator': 'MACD',
                'message': 'Bullish Crossover',
                'emoji': '📈'
            })
        elif prev['MACD_12_26_9'] > prev['MACDs_12_26_9'] and latest['MACD_12_26_9'] < latest['MACDs_12_26_9']:
            signals.append({
                'type': 'SELL',
                'strength': 'MEDIUM',
                'indicator': 'MACD',
                'message': 'Bearish Crossover',
                'emoji': '📉'
            })
        
        # Moving Average Crossover
        if latest['Close'] > latest['SMA_50'] and prev['Close'] < prev['SMA_50']:
            signals.append({
                'type': 'BUY',
                'strength': 'MEDIUM',
                'indicator': 'MA',
                'message': 'Price crossed above SMA 50',
                'emoji': '🎯'
            })
        
        # Bollinger Bands
        if latest['Close'] < latest['BBL_20_2.0']:
            signals.append({
                'type': 'BUY',
                'strength': 'WEAK',
                'indicator': 'BB',
                'message': 'Price below lower Bollinger Band',
                'emoji': '⚡'
            })
        elif latest['Close'] > latest['BBU_20_2.0']:
            signals.append({
                'type': 'SELL',
                'strength': 'WEAK',
                'indicator': 'BB',
                'message': 'Price above upper Bollinger Band',
                'emoji': '⚠️'
            })
        
        return signals

# Header
def render_header():
    """Render app header"""
    st.markdown(f"""
        <div class="app-header">
            <h1 class="app-title">📊 {AppConfig.APP_NAME}</h1>
            <p class="app-subtitle">Indian & Global Markets • Real-time Intelligence • AI-Powered Insights</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Status Bar
    col1, col2, col3, col4 = st.columns(4)
    
    status, status_type = MarketUtils.get_market_status()
    
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Market Status</div>
                <div class="metric-value">{status}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">IST Time</div>
                <div class="metric-value" style="font-size: 1.5rem;">{now.strftime('%I:%M %p')}</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        nifty_data, _ = IndianMarketData.get_stock_data('^NSEI', '1d')
        if nifty_data is not None and len(nifty_data) > 0:
            nifty_change = ((nifty_data['Close'].iloc[-1] - nifty_data['Open'].iloc[-1]) / nifty_data['Open'].iloc[-1]) * 100
            delta_class = 'metric-delta-positive' if nifty_change >= 0 else 'metric-delta-negative'
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">NIFTY 50</div>
                    <div class="metric-value" style="font-size: 1.5rem;">{nifty_data['Close'].iloc[-1]:.2f}</div>
                    <div class="{delta_class}">{nifty_change:+.2f}%</div>
                </div>
            """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Active Alerts</div>
                <div class="metric-value">{len(st.session_state.alerts)}</div>
            </div>
        """, unsafe_allow_html=True)

# Sidebar
def render_sidebar():
    """Render enhanced sidebar"""
    with st.sidebar:
        st.image("https://via.placeholder.com/200x80/667eea/ffffff?text=MEK+STOCK+ALERT", use_column_width=True)
        
        st.markdown("---")
        
        page = st.radio(
            "🧭 Navigation",
            [
                "🏠 Dashboard",
                "🇮🇳 Indian Markets",
                "🌍 Global Markets",
                "💼 Portfolio Tracker",
                "📊 Technical Analysis",
                "🔔 Alert Manager",
                "📰 News & Sentiment",
                "⚙️ Settings"
            ]
        )
        
        st.markdown("---")
        
        # Quick Stats
        st.subheader("📌 Quick Stats")
        
        # Portfolio Value
        if st.session_state.portfolio:
            total_value = sum([holding['shares'] * holding['current_price'] for holding in st.session_state.portfolio])
            st.metric("Portfolio Value", MarketUtils.format_inr(total_value))
        
        # Watchlist Count
        st.metric("Watchlist Items", len(st.session_state.watchlist))
        
        st.markdown("---")
        
        # Risk Profile Selector
        st.subheader("⚖️ Risk Profile")
        risk_profile = st.selectbox(
            "Select Profile",
            list(AppConfig.RISK_PROFILES.keys()),
            index=1
        )
        
        tranches = AppConfig.RISK_PROFILES[risk_profile]
        st.caption(f"Tranche 1: {tranches['t1']}% | T2: {tranches['t2']}% | T3: {tranches['t3']}%")
        
        st.markdown("---")
        
        # Quick Actions
        st.subheader("⚡ Quick Actions")
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.success("Data refreshed!")
        
        if st.button("📧 Send Test Alert", use_container_width=True):
            # Trigger test alert
            st.info("Test alert sent!")
        
        if st.button("📥 Export Portfolio", use_container_width=True):
            # Export portfolio as CSV
            if st.session_state.portfolio:
                df = pd.DataFrame(st.session_state.portfolio)
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    "portfolio.csv",
                    "text/csv"
                )
        
        st.markdown("---")
        
        # Footer
        st.caption(f"v{AppConfig.VERSION} | {AppConfig.AUTHOR}")
        st.caption("Made with ❤️ in India")
        
        return page

# Main App Logic
def main():
    render_header()
    page = render_sidebar()
    
    if page == "🏠 Dashboard":
        render_dashboard()
    elif page == "🇮🇳 Indian Markets":
        render_indian_markets()
    elif page == "🌍 Global Markets":
        render_global_markets()
    elif page == "💼 Portfolio Tracker":
        render_portfolio()
    elif page == "📊 Technical Analysis":
        render_technical_analysis()
    elif page == "🔔 Alert Manager":
        render_alert_manager()
    elif page == "📰 News & Sentiment":
        render_news()
    elif page == "⚙️ Settings":
        render_settings()

def render_dashboard():
    """Main dashboard view"""
    st.title("🏠 Market Dashboard")
    
    # Top Movers Section
    st.subheader("🔥 Top Movers Today")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Top Gainers")
        # Fetch and display top gainers
        # Placeholder data
        gainers_data = {
            'Stock': ['RELIANCE', 'TCS', 'INFY'],
            'Price': [2450.50, 3210.75, 1540.20],
            'Change %': ['+5.2%', '+3.8%', '+3.1%']
        }
        st.dataframe(pd.DataFrame(gainers_data), use_container_width=True)
    
    with col2:
        st.markdown("### 📉 Top Losers")
        losers_data = {
            'Stock': ['HDFC BANK', 'ICICI BANK', 'SBIN'],
            'Price': [1620.30, 890.45, 545.60],
            'Change %': ['-2.8%', '-2.1%', '-1.9%']
        }
        st.dataframe(pd.DataFrame(losers_data), use_container_width=True)
    
    st.markdown("---")
    
    # Mutual Funds Section
    st.subheader("💰 Your Mutual Funds Performance")
    
    mf_data = []
    for fund in AppConfig.TRACKED_MUTUAL_FUNDS:
        nav_data = IndianMarketData.get_mutual_fund_nav(fund['amfi'])
        if nav_data:
            mf_data.append({
                'Fund Name': fund['name'],
                'NAV': f"₹{nav_data['nav']:.2f}",
                'Category': fund['category'],
                'Rating': '⭐' * fund['rating'],
                'Last Updated': nav_data['date']
            })
    
    if mf_data:
        st.dataframe(pd.DataFrame(mf_data), use_container_width=True)
    
    st.markdown("---")
    
    # Recent Alerts
    st.subheader("🔔 Recent Alerts")
    
    if st.session_state.alerts:
        for alert in st.session_state.alerts[-5:]:  # Show last 5
            alert_type = alert.get('type', 'info')
            st.markdown(f"""
                <div class="alert-{alert_type}">
                    {alert.get('message', 'No message')}
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No recent alerts")

def render_indian_markets():
    """Indian markets detailed view"""
    st.title("🇮🇳 Indian Markets")
    
    tab1, tab2, tab3 = st.tabs(["📊 Nifty 100 Scanner", "💎 Mutual Funds", "🎯 Dip Calculator"])
    
    with tab1:
        st.subheader("Nifty 100 Live Scanner")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            min_drop = st.slider("Minimum Drop %", 0.0, 10.0, 2.0, 0.5)
        with col2:
            sector_filter = st.multiselect("Sector", ["All", "Banking", "IT", "Pharma", "Auto"])
        with col3:
            sort_by = st.selectbox("Sort By", ["Drop %", "Volume", "Recovery Upside"])
        
        if st.button("🔍 Scan Now", use_container_width=True):
            with st.spinner("Scanning Nifty 100..."):
                # Implement scanning logic
                st.success("Scan complete!")
    
    with tab2:
        st.subheader("Your 9 Mutual Funds")
        
        # Display detailed MF analysis
        for fund in AppConfig.TRACKED_MUTUAL_FUNDS:
            with st.expander(f"{fund['name']} - {fund['category']}"):
                nav_data = IndianMarketData.get_mutual_fund_nav(fund['amfi'])
                if nav_data:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Current NAV", f"₹{nav_data['nav']:.2f}")
                    with col2:
                        st.metric("Rating", '⭐' * fund['rating'])
                    with col3:
                        st.metric("Last Updated", nav_data['date'])
    
    with tab3:
        st.subheader("Dip & Recovery Calculator")
        
        col1, col2 = st.columns(2)
        
        with col1:
            investment_amount = st.number_input("Investment Amount (₹)", 10000, 10000000, 100000, 10000)
            buy_price = st.number_input("Buy Price (₹)", 1.0, 100000.0, 100.0, 0.1)
            target_price = st.number_input("Target Price (₹)", 1.0, 100000.0, 120.0, 0.1)
        
        with col2:
            shares = investment_amount / buy_price
            potential_profit = (target_price - buy_price) * shares
            roi = ((target_price - buy_price) / buy_price) * 100
            
            st.metric("Shares", f"{shares:.2f}")
            st.metric("Potential Profit", MarketUtils.format_inr(potential_profit))
            st.metric("ROI %", f"{roi:.2f}%")

def render_global_markets():
    """Global markets view"""
    st.title("🌍 Global Markets")
    
    tab1, tab2, tab3 = st.tabs(["🇺🇸 US Markets", "💰 Crypto", "🌏 Other Markets"])
    
    with tab1:
        st.subheader("US Stock Markets")
        
        # Major indices
        col1, col2, col3 = st.columns(3)
        
        indices = {
            'S&P 500': '^GSPC',
            'NASDAQ': '^IXIC',
            'DOW JONES': '^DJI'
        }
        
        for idx, (name, symbol) in enumerate(indices.items()):
            with [col1, col2, col3][idx]:
                df, info = IndianMarketData.get_stock_data(symbol, '1d')
                if df is not None and len(df) > 0:
                    current_price = df['Close'].iloc[-1]
                    change_pct = ((df['Close'].iloc[-1] - df['Open'].iloc[-1]) / df['Open'].iloc[-1]) * 100
                    st.metric(name, f"{current_price:.2f}", f"{change_pct:+.2f}%")
    
    with tab2:
        st.subheader("Cryptocurrency Markets")
        
        cryptos = ['BTC-USD', 'ETH-USD', 'BNB-USD']
        
        for crypto in cryptos:
            df, info = IndianMarketData.get_stock_data(crypto, '1d')
            if df is not None and len(df) > 0:
                col1, col2, col3, col4 = st.columns(4)
                
                current_price = df['Close'].iloc[-1]
                change_pct = ((df['Close'].iloc[-1] - df['Open'].iloc[-1]) / df['Open'].iloc[-1]) * 100
                volume = df['Volume'].iloc[-1]
                
                with col1:
                    st.metric(crypto.replace('-USD', ''), f"${current_price:,.2f}")
                with col2:
                    st.metric("24h Change", f"{change_pct:+.2f}%")
                with col3:
                    st.metric("Volume", f"${volume/1e9:.2f}B")
                with col4:
                    st.button(f"Analyze {crypto}", key=crypto)
    
    with tab3:
        st.info("Other international markets coming soon!")

def render_portfolio():
    """Portfolio tracker"""
    st.title("💼 Portfolio Tracker")
    
    tab1, tab2 = st.tabs(["📊 Overview", "➕ Add Holdings"])
    
    with tab1:
        if st.session_state.portfolio:
            # Calculate portfolio metrics
            total_value = 0
            total_cost = 0
            
            portfolio_data = []
            
            for holding in st.session_state.portfolio:
                # Fetch current price
                df, _ = IndianMarketData.get_stock_data(holding['symbol'], '1d')
                if df is not None and len(df) > 0:
                    current_price = df['Close'].iloc[-1]
                    value = holding['shares'] * current_price
                    cost = holding['shares'] * holding['buy_price']
                    profit_loss = value - cost
                    roi = (profit_loss / cost) * 100
                    
                    total_value += value
                    total_cost += cost
                    
                    portfolio_data.append({
                        'Symbol': holding['symbol'],
                        'Shares': holding['shares'],
                        'Buy Price': f"₹{holding['buy_price']:.2f}",
                        'Current Price': f"₹{current_price:.2f}",
                        'Current Value': MarketUtils.format_inr(value),
                        'P&L': MarketUtils.format_inr(profit_loss),
                        'ROI %': f"{roi:.2f}%"
                    })
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Value", MarketUtils.format_inr(total_value))
            with col2:
                st.metric("Total Cost", MarketUtils.format_inr(total_cost))
            with col3:
                st.metric("Total P&L", MarketUtils.format_inr(total_value - total_cost))
            with col4:
                roi = ((total_value - total_cost) / total_cost) * 100
                st.metric("Portfolio ROI", f"{roi:.2f}%")
            
            # Portfolio table
            st.dataframe(pd.DataFrame(portfolio_data), use_container_width=True)
            
        else:
            st.info("Your portfolio is empty. Add holdings from the 'Add Holdings' tab.")
    
    with tab2:
        st.subheader("Add New Holding")
        
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.text_input("Stock Symbol (e.g., RELIANCE.NS)").upper()
            shares = st.number_input("Number of Shares", 1, 100000, 10)
        
        with col2:
            buy_price = st.number_input("Buy Price (₹)", 1.0, 100000.0, 100.0, 0.1)
            buy_date = st.date_input("Purchase Date")
        
        if st.button("➕ Add to Portfolio", use_container_width=True):
            st.session_state.portfolio.append({
                'symbol': symbol,
                'shares': shares,
                'buy_price': buy_price,
                'buy_date': buy_date
            })
            st.success(f"Added {shares} shares of {symbol} to portfolio!")
            st.rerun()

def render_technical_analysis():
    """Advanced technical analysis"""
    st.title("📊 Technical Analysis")
    
    # Stock selector
    symbol = st.text_input("Enter Stock Symbol", "RELIANCE.NS").upper()
    timeframe = st.selectbox("Timeframe", ["1D", "1W", "1M", "3M", "6M", "1Y"])
    
    period_map = {
        '1D': '1d',
        '1W': '5d',
        '1M': '1mo',
        '3M': '3mo',
        '6M': '6mo',
        '1Y': '1y'
    }
    
    if st.button("📈 Analyze", use_container_width=True):
        with st.spinner(f"Analyzing {symbol}..."):
            df, info = IndianMarketData.get_stock_data(symbol, period_map[timeframe])
            
            if df is not None and len(df) > 0:
                # Calculate indicators
                df = TechnicalAnalysis.calculate_all_indicators(df)
                
                # Create advanced chart
                fig = make_subplots(
                    rows=4, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.03,
                    subplot_titles=(f'{symbol} Price & Indicators', 'MACD', 'RSI', 'Volume'),
                    row_heights=[0.4, 0.2, 0.2, 0.2]
                )
                
                # Candlestick
                fig.add_trace(
                    go.Candlestick(
                        x=df.index,
                        open=df['Open'],
                        high=df['High'],
                        low=df['Low'],
                        close=df['Close'],
                        name='OHLC'
                    ),
                    row=1, col=1
                )
                
                # Moving Averages
                for ma, color in [('SMA_20', 'orange'), ('SMA_50', 'blue'), ('SMA_200', 'red')]:
                    if ma in df.columns:
                        fig.add_trace(
                            go.Scatter(
                                x=df.index,
                                y=df[ma],
                                name=ma,
                                line=dict(color=color, width=1)
                            ),
                            row=1, col=1
                        )
                
                # Bollinger Bands
                if 'BBU_20_2.0' in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['BBU_20_2.0'],
                            name='Upper BB',
                            line=dict(color='gray', width=1, dash='dash')
                        ),
                        row=1, col=1
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['BBL_20_2.0'],
                            name='Lower BB',
                            line=dict(color='gray', width=1, dash='dash'),
                            fill='tonexty',
                            fillcolor='rgba(128, 128, 128, 0.1)'
                        ),
                        row=1, col=1
                    )
                
                # MACD
                if 'MACD_12_26_9' in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['MACD_12_26_9'],
                            name='MACD',
                            line=dict(color='blue', width=1)
                        ),
                        row=2, col=1
                    )
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['MACDs_12_26_9'],
                            name='Signal',
                            line=dict(color='orange', width=1)
                        ),
                        row=2, col=1
                    )
                    fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=df['MACDh_12_26_9'],
                            name='Histogram',
                            marker_color='gray'
                        ),
                        row=2, col=1
                    )
                
                # RSI
                if 'RSI' in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df['RSI'],
                            name='RSI',
                            line=dict(color='purple', width=2)
                        ),
                        row=3, col=1
                    )
                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
                    fig.add_hline(y=50, line_dash="dot", line_color="gray", row=3, col=1)
                
                # Volume
                colors = ['red' if df['Close'].iloc[i] < df['Open'].iloc[i] else 'green' for i in range(len(df))]
                fig.add_trace(
                    go.Bar(
                        x=df.index,
                        y=df['Volume'],
                        name='Volume',
                        marker_color=colors
                    ),
                    row=4, col=1
                )
                
                fig.update_layout(
                    height=1000,
                    showlegend=True,
                    xaxis_rangeslider_visible=False,
                    template='plotly_dark'
                )
                
                fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(128, 128, 128, 0.2)')
                fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(128, 128, 128, 0.2)')
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Trading Signals
                st.subheader("🎯 Trading Signals")
                
                signals = TechnicalAnalysis.generate_signals(df)
                
                if signals:
                    col1, col2 = st.columns(2)
                    
                    buy_signals = [s for s in signals if s['type'] == 'BUY']
                    sell_signals = [s for s in signals if s['type'] == 'SELL']
                    
                    with col1:
                        st.markdown("### 🟢 Buy Signals")
                        for signal in buy_signals:
                            st.markdown(f"""
                                <div class="alert-success">
                                    {signal['emoji']} <strong>{signal['indicator']}</strong>: {signal['message']} (Strength: {signal['strength']})
                                </div>
                            """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("### 🔴 Sell Signals")
                        for signal in sell_signals:
                            st.markdown(f"""
                                <div class="alert-danger">
                                    {signal['emoji']} <strong>{signal['indicator']}</strong>: {signal['message']} (Strength: {signal['strength']})
                                </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No strong signals detected at this time.")
                
                # Key Metrics
                st.subheader("📊 Key Metrics")
                
                latest = df.iloc[-1]
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Current Price", f"₹{latest['Close']:.2f}")
                    st.metric("RSI", f"{latest['RSI']:.2f}")
                
                with col2:
                    st.metric("SMA 20", f"₹{latest['SMA_20']:.2f}")
                    st.metric("SMA 50", f"₹{latest['SMA_50']:.2f}")
                
                with col3:
                    if 'MACD_12_26_9' in latest:
                        st.metric("MACD", f"{latest['MACD_12_26_9']:.2f}")
                    if 'ATR' in latest:
                        st.metric("ATR (Volatility)", f"{latest['ATR']:.2f}")
                
                with col4:
                    st.metric("Volume", f"{latest['Volume']:,.0f}")
                    if 'OBV' in latest:
                        st.metric("OBV", f"{latest['OBV']:,.0f}")

def render_alert_manager():
    """Alert management system"""
    st.title("🔔 Alert Manager")
    
    tab1, tab2, tab3 = st.tabs(["📋 Active Alerts", "➕ Create Alert", "⚙️ Alert Settings"])
    
    with tab1:
        st.subheader("Your Active Alerts")
        
        if st.session_state.alerts:
            for idx, alert in enumerate(st.session_state.alerts):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"""
                        <div class="alert-info">
                            <strong>{alert['symbol']}</strong>: {alert['condition']} ₹{alert['target']:.2f}
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.caption(f"Created: {alert['created']}")
                
                with col3:
                    if st.button("🗑️ Delete", key=f"del_{idx}"):
                        st.session_state.alerts.pop(idx)
                        st.rerun()
        else:
            st.info("No active alerts. Create one using the 'Create Alert' tab.")
    
    with tab2:
        st.subheader("Create New Price Alert")
        
        col1, col2 = st.columns(2)
        
        with col1:
            alert_symbol = st.text_input("Stock Symbol", "RELIANCE.NS").upper()
            alert_condition = st.selectbox("Condition", ["Price Above", "Price Below", "Drop %", "Gain %"])
        
        with col2:
            if "Drop %" in alert_condition or "Gain %" in alert_condition:
                alert_target = st.number_input("Percentage", 0.0, 100.0, 5.0, 0.5)
            else:
                alert_target = st.number_input("Target Price (₹)", 1.0, 100000.0, 100.0, 0.1)
            
            alert_channel = st.multiselect("Alert Channels", ["Telegram", "Email", "SMS"])
        
        if st.button("✅ Create Alert", use_container_width=True):
            st.session_state.alerts.append({
                'symbol': alert_symbol,
                'condition': alert_condition,
                'target': alert_target,
                'channels': alert_channel,
                'created': datetime.now().strftime('%Y-%m-%d %H:%M')
            })
            st.success(f"Alert created for {alert_symbol}!")
            st.rerun()
    
    with tab3:
        st.subheader("Alert Settings")
        
        st.checkbox("Enable Telegram Notifications", value=True)
        st.checkbox("Enable Email Notifications", value=True)
        st.checkbox("Enable SMS Notifications", value=False)
        
        st.slider("Alert Check Frequency (minutes)", 1, 60, 5)
        
        st.time_input("Quiet Hours Start", datetime.strptime("22:00", "%H:%M").time())
        st.time_input("Quiet Hours End", datetime.strptime("07:00", "%H:%M").time())

def render_news():
    """News and sentiment analysis"""
    st.title("📰 News & Sentiment Analysis")
    
    symbol = st.text_input("Enter Stock Symbol for News", "RELIANCE").upper()
    
    if st.button("🔍 Fetch Latest News", use_container_width=True):
        st.info("News integration coming soon! This will show latest news from Economic Times, Moneycontrol, and other sources.")
        
        # Placeholder news items
        news_items = [
            {
                'title': 'Market hits new high on strong earnings',
                'source': 'Economic Times',
                'sentiment': 'Positive',
                'time': '2 hours ago'
            },
            {
                'title': 'Tech stocks under pressure amid global sell-off',
                'source': 'Moneycontrol',
                'sentiment': 'Negative',
                'time': '4 hours ago'
            }
        ]
        
        for news in news_items:
            sentiment_class = 'success' if news['sentiment'] == 'Positive' else 'warning'
            st.markdown(f"""
                <div class="alert-{sentiment_class}">
                    <strong>{news['title']}</strong><br>
                    <small>{news['source']} • {news['time']} • Sentiment: {news['sentiment']}</small>
                </div>
            """, unsafe_allow_html=True)

def render_settings():
    """App settings"""
    st.title("⚙️ Settings")
    
    tab1, tab2, tab3 = st.tabs(["👤 Profile", "🔔 Notifications", "🎨 Appearance"])
    
    with tab1:
        st.subheader("Your Profile")
        
        st.text_input("Email", AppConfig.SENDER_EMAIL)
        st.text_input("Telegram Chat ID", AppConfig.TELEGRAM_CHAT_ID if AppConfig.TELEGRAM_CHAT_ID else "Not configured")
        
        st.selectbox("Default Risk Profile", list(AppConfig.RISK_PROFILES.keys()), index=1)
        st.selectbox("Default Market", ["Indian Markets", "Global Markets"])
    
    with tab2:
        st.subheader("Notification Preferences")
        
        st.checkbox("Email Alerts", value=True)
        st.checkbox("Telegram Alerts", value=True)
        st.checkbox("SMS Alerts", value=False)
        
        st.multiselect(
            "Alert Types",
            ["Price Alerts", "Technical Signals", "News Updates", "Portfolio Updates"],
            default=["Price Alerts", "Technical Signals"]
        )
    
    with tab3:
        st.subheader("Appearance")
        
        theme = st.selectbox("Theme", ["Dark (Default)", "Light", "Auto"])
        st.selectbox("Chart Style", ["Plotly Dark", "Plotly White", "Seaborn"])
        st.checkbox("Show Animations", value=True)

if __name__ == "__main__":
    main()
