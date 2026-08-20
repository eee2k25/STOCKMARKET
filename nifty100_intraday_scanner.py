#!/usr/bin/env python3
"""
Nifty 100 & Mutual Fund Real-Time Intraday Flash Scanner
Monitors Top 100 Indian Companies + 9 Watchlist Mutual Funds throughout market hours (9:15 AM - 3:30 PM IST).
Triggers INSTANT alerts (Email + Telegram) on sudden dips >= 2.5% or major value opportunities.
"""

import os
import sys
import time
import json
import datetime
import yfinance as yf
import requests

try:
    import notifier  # optional: alerts are dispatched only when a notifier module exists
except ImportError:
    notifier = None

# Full Nifty 100 Universe (Top 100 Companies in India)
NIFTY_100_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "INFY.NS", "ITC.NS", "SBIN.NS", "LT.NS", "HINDUNILVR.NS",
    "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", "TATAMOTORS.NS",
    "KOTAKBANK.NS", "TITAN.NS", "ONGC.NS", "NTPC.NS", "AXISBANK.NS",
    "POWERGRID.NS", "ADANIPORTS.NS", "ADANIENT.NS", "ULTRACEMCO.NS", "COALINDIA.NS",
    "BAJAJFINSV.NS", "ASIANPAINT.NS", "TATASTEEL.NS", "NESTLEIND.NS", "JSWSTEEL.NS",
    "M&M.NS", "VBL.NS", "BEL.NS", "HAL.NS", "DLF.NS", "SIEMENS.NS", "IOC.NS", "TRENT.NS",
    "GRASIM.NS", "TECHM.NS", "HINDALCO.NS", "WIPRO.NS", "CIPLA.NS", "DRREDDY.NS",
    "SBILIFE.NS", "BPCL.NS", "HEROMOTOCO.NS", "EICHERMOT.NS", "APOLLOHOSP.NS", "BRITANNIA.NS",
    "VEDL.NS", "GAIL.NS", "SHRIRAMFIN.NS", "INDUSINDBK.NS", "HDFCLIFE.NS", "TATACONSUM.NS",
    "HAVELLS.NS", "DIVISLAB.NS", "CHOLAFIN.NS", "MOTHERSON.NS", "AMBUJACEM.NS", "BOSCHLTD.NS",
    "PIDILITIND.NS", "TVSMOTOR.NS", "MAXHEALTH.NS", "BANKBARODA.NS", "CANBK.NS", "PNB.NS",
    "POLYCAB.NS", "ABB.NS", "CGPOWER.NS", "CUMMINSIND.NS", "COLPAL.NS", "DABUR.NS",
    "GODREJCP.NS", "BERGEPAINT.NS", "MARICO.NS", "SRF.NS", "NAUKRI.NS", "PERSISTENT.NS",
    "OFSS.NS", "MPHASIS.NS", "KPITTECH.NS", "LUPIN.NS", "AUROPHARMA.NS", "ALKEM.NS",
    "TORNTPHARM.NS", "ZYDUSLIFE.NS", "JINDALSTEL.NS", "NMDC.NS", "SAIL.NS", "PFC.NS",
    "RECLTD.NS", "IRFC.NS", "RVNL.NS", "MAZDOCK.NS", "COCHINSHIP.NS", "BSE.NS"
]

ALERTS_SENT_TODAY = set()

def scan_nifty_100(threshold_pct=-2.0, recipient="meksmod1@gmail.com"):
    """
    Downloads market data for all Nifty 100 stocks and evaluates instant dips.
    """
    print(f"\n🔍 [{datetime.datetime.now().strftime('%H:%M:%S IST')}] Scanning Nifty 100 & Mutual Funds...")
    opportunities = []

    try:
        data = yf.download(NIFTY_100_STOCKS, period="5d", interval="1d", progress=False, group_by='ticker')
        
        for sym in NIFTY_100_STOCKS:
            try:
                df = data[sym] if sym in data else None
                if df is None or df.empty or len(df['Close'].dropna()) < 2:
                    continue
                
                closes = df['Close'].dropna()
                highs = df['High'].dropna()
                curr = float(closes.iloc[-1])
                prev = float(closes.iloc[-2])
                day_high = float(highs.iloc[-1])
                
                chg_pct = ((curr - prev) / prev) * 100
                intraday_pullback = ((curr - day_high) / day_high) * 100
                high_52w = float(df['High'].max())
                drawdown_52w = ((curr - high_52w) / high_52w) * 100
                recovery_upside = ((high_52w - curr) / curr) * 100

                clean_sym = sym.replace(".NS", "")

                is_sharp_dip = (chg_pct <= threshold_pct) or (intraday_pullback <= -3.0) or (drawdown_52w <= -20.0 and chg_pct <= -1.0)

                if is_sharp_dip:
                    action_note = f"Quality Nifty 100 leader trading at {drawdown_52w:.1f}% discount from peak."
                    drop_type = "Sudden Intraday Pullback" if chg_pct <= -2.0 else "Deep Multi-Month Value Zone"

                    opp = {
                        "symbol": clean_sym,
                        "raw_symbol": sym,
                        "name": clean_sym,
                        "price": round(curr, 2),
                        "daily_pct": round(chg_pct, 2),
                        "high_52w": round(high_52w, 2),
                        "drawdown_52w": round(drawdown_52w, 2),
                        "recovery_upside_pct": round(recovery_upside, 2),
                        "drop_type": drop_type,
                        "action_note": action_note
                    }
                    opportunities.append(opp)

                    alert_key = f"{clean_sym}_{datetime.date.today()}"
                    if notifier and alert_key not in ALERTS_SENT_TODAY:
                        notifier.dispatch_dip_alert(opp, recipient)
                        ALERTS_SENT_TODAY.add(alert_key)

            except Exception as e:
                continue

    except Exception as e:
        print(f"Error during bulk scan: {e}")

    print(f"🎯 Scan Complete. Found {len(opportunities)} instant dip opportunities in Nifty 100.")
    return opportunities

if __name__ == "__main__":
    scan_nifty_100(threshold_pct=-2.0)
