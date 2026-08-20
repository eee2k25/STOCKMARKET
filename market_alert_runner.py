import os
import sys
import datetime
import requests
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

USER_FUNDS = {
    "119783": {"name": "SBI Healthcare Opportunities Fund (Direct-Growth)", "category": "Pharma"},
    "113049": {"name": "HDFC Gold ETF Fund", "category": "Gold"},
    "119788": {"name": "SBI Gold Fund (Direct-Growth)", "category": "Gold"},
    "118551": {"name": "Franklin U.S. Opportunities Equity Active FoF", "category": "International"},
    "118736": {"name": "Nippon India Balanced Advantage Fund", "category": "Hybrid"},
    "118778": {"name": "Nippon India Small Cap Fund", "category": "Small Cap"},
    "147662": {"name": "ICICI Prudential Commodities Fund", "category": "Commodities"},
    "120578": {"name": "SBI Technology Opportunities Fund", "category": "Technology"},
    "120594": {"name": "ICICI Prudential Technology Fund", "category": "Technology"}
}

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

def send_telegram(message_html):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        print("⚠️ Telegram credentials missing.")
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "text": message_html, "parse_mode": "HTML"}, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def send_email(subject, html_body, recipient="meksmod1@gmail.com"):
    sender = os.environ.get("SENDER_EMAIL", "meksmod1@gmail.com")
    pwd = os.environ.get("SENDER_APP_PASSWORD", "")
    if not pwd:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Stock Dip Advisor <{sender}>"
        msg["To"] = recipient
        msg.attach(MIMEText(html_body, "html"))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, pwd)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        return True
    except Exception:
        return False

def run_scan():
    nifty_price = 24244.15
    nifty_chg = -0.50
    try:
        tk = yf.Ticker("^NSEI")
        hist = tk.history(period="5d")
        if len(hist) >= 2:
            nifty_price = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2])
            nifty_chg = ((nifty_price - prev)/prev)*100
    except Exception:
        pass

    fund_dips = []
    for code, meta in USER_FUNDS.items():
        try:
            r = requests.get(f"https://api.mfapi.in/mf/{code}", timeout=6)
            if r.status_code == 200:
                navs = r.json().get("data", [])
                if len(navs) >= 2:
                    curr = float(navs[0]["nav"])
                    prev = float(navs[1]["nav"])
                    high = max([float(x["nav"]) for x in navs[:250]])
                    dd = ((curr - high)/high)*100
                    upside = ((high - curr)/curr)*100
                    if dd <= -5.0 or ((curr-prev)/prev)*100 <= -0.5:
                        fund_dips.append({"name": meta["name"], "nav": curr, "dd": dd, "upside": upside})
        except Exception:
            continue

    stock_dips = []
    try:
        data = yf.download(NIFTY_100_STOCKS, period="5d", interval="1d", progress=False, group_by='ticker')
        for sym in NIFTY_100_STOCKS:
            try:
                df = data[sym] if sym in data else None
                if df is None or df.empty or len(df['Close'].dropna()) < 2:
                    continue
                closes = df['Close'].dropna()
                curr = float(closes.iloc[-1])
                prev = float(closes.iloc[-2])
                chg = ((curr - prev)/prev)*100
                high = float(df['High'].max())
                dd = ((curr - high)/high)*100
                upside = ((high - curr)/curr)*100
                clean = sym.replace(".NS", "")
                if chg <= -1.8 or (dd <= -18.0 and chg <= -0.5):
                    stock_dips.append({"symbol": clean, "price": curr, "chg": chg, "high": high, "dd": dd, "upside": upside})
            except Exception:
                continue
    except Exception:
        pass

    now_str = datetime.datetime.now().strftime("%d-%b-%Y %H:%M IST")
    tg_msg = f"📈 <b>NIFTY 100 & MF DIP REPORT</b>\n⏰ <i>{now_str}</i> | Nifty: <b>₹{nifty_price:,.2f} ({nifty_chg:+.2f}%)</b>\n\n"
    if stock_dips:
        tg_msg += "🏢 <b>TOP NIFTY 100 STOCK DIPS:</b>\n"
        for s in stock_dips[:4]:
            tg_msg += f"• <b>{s['symbol']}</b>: ₹{s['price']:,.2f} (<b>{s['chg']:+.2f}%</b>)\n  └ Peak: ₹{s['high']:,.2f} | <b>+{s['upside']:.1f}% Upside</b>\n"
        tg_msg += "\n"
    if fund_dips:
        tg_msg += "📊 <b>MUTUAL FUNDS IN DISCOUNT:</b>\n"
        for f in fund_dips[:3]:
            tg_msg += f"• <b>{f['name']}</b>\n  └ Discount: <b>{f['dd']:.1f}%</b> | <b>+{f['upside']:.1f}% Upside</b>\n"
        tg_msg += "\n"
    tg_msg += "🛡️ <b>Moderate Action:</b> Deploy <b>Tranche 1 (30%)</b>. Keep 70% cash reserve."

    send_telegram(tg_msg)
    send_email(f"📈 Market Dip Alert ({now_str})", tg_msg.replace("\n", "<br>"), "meksmod1@gmail.com")
    print("✅ Alert executed successfully!")

if __name__ == "__main__":
    run_scan()
