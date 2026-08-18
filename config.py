# config.py - Centralized Configuration
import os
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class AppConfig:
    """Application configuration"""
    APP_NAME = "MEK Stock Alert Pro"
    VERSION = "2.0"
    AUTHOR = "MEK Trading Systems"
    
    # Email Configuration
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'meksmod1@gmail.com')
    SENDER_APP_PASSWORD = os.getenv('SENDER_APP_PASSWORD')
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # Alert Thresholds
    INTRADAY_DROP_THRESHOLD = 2.0  # %
    DISCOUNT_THRESHOLD = 15.0  # %
    
    # Trading Hours IST
    MARKET_OPEN = "09:15"
    MARKET_CLOSE = "15:30"
    
    # Risk Profiles
    RISK_PROFILES = {
        'Conservative': {'t1': 20, 't2': 30, 't3': 50},
        'Moderate': {'t1': 30, 't2': 30, 't3': 40},
        'Aggressive': {'t1': 40, 't2': 35, 't3': 25}
    }
    
    # Your 9 Mutual Funds
    TRACKED_MUTUAL_FUNDS = [
        {'name': 'SBI Healthcare Opportunities Fund', 'amfi': '119783', 'category': 'Sectoral Pharma', 'rating': 5},
        {'name': 'HDFC Gold ETF Fund', 'amfi': '113049', 'category': 'Commodities Gold', 'rating': 3},
        {'name': 'SBI Gold Fund', 'amfi': '119788', 'category': 'Commodities Gold', 'rating': 4},
        {'name': 'Franklin U.S. Opportunities Equity FoF', 'amfi': '118551', 'category': 'International Equity', 'rating': 4},
        {'name': 'Nippon India Balanced Advantage Fund', 'amfi': '118736', 'category': 'Hybrid Dynamic', 'rating': 4},
        {'name': 'Nippon India Small Cap Fund', 'amfi': '118778', 'category': 'Equity Small Cap', 'rating': 4},
        {'name': 'ICICI Prudential Commodities Fund', 'amfi': '147662', 'category': 'Thematic Commodities', 'rating': 3},
        {'name': 'SBI Technology Opportunities Fund', 'amfi': '120578', 'category': 'Sectoral Technology', 'rating': 4},
        {'name': 'ICICI Prudential Technology Fund', 'amfi': '120594', 'category': 'Sectoral Technology', 'rating': 4}
    ]
    
    # Nifty 100 Stocks (Top 30 for now - you can add all 100 later)
    NIFTY_100_STOCKS = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
        "ICICIBANK.NS", "KOTAKBANK.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS",
        "AXISBANK.NS", "LT.NS", "ASIANPAINT.NS", "MARUTI.NS", "HCLTECH.NS",
        "BAJFINANCE.NS", "WIPRO.NS", "ULTRACEMCO.NS", "TITAN.NS", "NESTLEIND.NS",
        "SUNPHARMA.NS", "TECHM.NS", "POWERGRID.NS", "NTPC.NS", "ONGC.NS",
        "TATASTEEL.NS", "M&M.NS", "ADANIENT.NS", "JSWSTEEL.NS", "INDUSINDBK.NS"
    ]
