import os
import json
import datetime
import requests
import yfinance as yf
from flask import Flask, render_template_string, jsonify, request
import nifty100_intraday_scanner as scanner

app = Flask(__name__)

CONFIG_FILE = "user_config.json"

DEFAULT_CONFIG = {
    "email": "meksmod1@gmail.com",
    "risk_profile": "moderate",
    "alert_frequency": "instant_and_eod",
    "dip_threshold": 2.5,
    "funds": {
        "119783": {"name": "SBI Healthcare Opportunities Fund (Direct-Growth)", "category": "Sectoral - Healthcare", "rating": "5★"},
        "113049": {"name": "HDFC Gold ETF Fund", "category": "Commodities - Gold", "rating": "3★"},
        "119788": {"name": "SBI Gold Fund (Direct-Growth)", "category": "Commodities - Gold", "rating": "4★"},
        "118551": {"name": "Franklin U.S. Opportunities Equity Active FoF (Direct-Growth)", "category": "International Equity", "rating": "Active"},
        "118736": {"name": "Nippon India Balanced Advantage Fund (Direct-Growth)", "category": "Hybrid Dynamic Asset Allocation", "rating": "4★"},
        "118778": {"name": "Nippon India Small Cap Fund (Direct-Growth)", "category": "Equity - Small Cap", "rating": "4★"},
        "147662": {"name": "ICICI Prudential Commodities Fund (Direct-Growth)", "category": "Thematic - Commodities", "rating": "Thematic"},
        "120578": {"name": "SBI Technology Opportunities Fund (Direct-Growth)", "category": "Sectoral - Technology", "rating": "Sectoral"},
        "120594": {"name": "ICICI Prudential Technology Fund (Direct-Growth)", "category": "Sectoral - Technology", "rating": "Sectoral"}
    },
    "stocks": {
        "RELIANCE.NS": {"name": "Reliance Industries Ltd", "sector": "Energy / Retail"},
        "HDFCBANK.NS": {"name": "HDFC Bank Ltd", "sector": "Private Banking"},
        "ICICIBANK.NS": {"name": "ICICI Bank Ltd", "sector": "Private Banking"},
        "TCS.NS": {"name": "Tata Consultancy Services", "sector": "IT Services"},
        "INFY.NS": {"name": "Infosys Ltd", "sector": "IT Services"},
        "LT.NS": {"name": "Larsen & Toubro Ltd", "sector": "Infrastructure"},
        "BHARTIARTL.NS": {"name": "Bharti Airtel Ltd", "sector": "Telecom"},
        "ITC.NS": {"name": "ITC Ltd", "sector": "FMCG / Diversified"},
        "SBIN.NS": {"name": "State Bank of India", "sector": "PSU Banking"},
        "SUNPHARMA.NS": {"name": "Sun Pharma Ltd", "sector": "Healthcare"}
    }
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

@app.route("/api/data", methods=["GET"])
def get_market_data():
    cfg = load_config()
    
    nifty_data = {"symbol": "NIFTY 50", "price": 24244.15, "change": -121.85, "pct_change": -0.50, "high_52w": 24774.30}
    try:
        tk = yf.Ticker("^NSEI")
        hist = tk.history(period="1mo")
        if not hist.empty and len(hist) >= 2:
            curr = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2])
            nifty_data = {
                "symbol": "NIFTY 50",
                "price": round(curr, 2),
                "change": round(curr - prev, 2),
                "pct_change": round(((curr - prev) / prev) * 100, 2),
                "high_52w": round(float(hist['High'].max()), 2)
            }
    except Exception as e:
        print("Nifty error:", e)

    funds_list = []
    for code, meta in cfg["funds"].items():
        try:
            r = requests.get(f"https://api.mfapi.in/mf/{code}", timeout=8)
            if r.status_code == 200:
                data = r.json()
                nav_list = data.get("data", [])
                if len(nav_list) >= 2:
                    curr_nav = float(nav_list[0]["nav"])
                    prev_nav = float(nav_list[1]["nav"])
                    navs_1y = [float(x["nav"]) for x in nav_list[:250]]
                    high_52w = max(navs_1y) if navs_1y else curr_nav
                    change = curr_nav - prev_nav
                    pct_change = (change / prev_nav) * 100
                    drawdown = ((curr_nav - high_52w) / high_52w) * 100
                    upside = ((high_52w - curr_nav) / curr_nav) * 100

                    badge = "danger" if drawdown <= -10.0 else ("warning" if drawdown <= -4.0 else "success")
                    status = "High Conviction Dip" if drawdown <= -10.0 else ("Value Pullback" if drawdown <= -4.0 else "Holding Support")

                    funds_list.append({
                        "code": code,
                        "name": meta["name"],
                        "category": meta["category"],
                        "rating": meta.get("rating", "4★"),
                        "nav": round(curr_nav, 2),
                        "date": nav_list[0]["date"],
                        "change": round(change, 2),
                        "pct_change": round(pct_change, 2),
                        "high_52w": round(high_52w, 2),
                        "drawdown_52w": round(drawdown, 2),
                        "recovery_upside_pct": round(upside, 2),
                        "status": status,
                        "badge": badge
                    })
        except Exception as e:
            print(f"Fund {code} err:", e)

    stocks_list = []
    for sym, meta in cfg["stocks"].items():
        try:
            tk = yf.Ticker(sym)
            hist = tk.history(period="1y")
            if not hist.empty and len(hist) >= 2:
                curr = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2])
                high_52w = float(hist['High'].max())
                change = curr - prev
                pct_change = (change / prev) * 100
                drawdown = ((curr - high_52w) / high_52w) * 100
                upside = ((high_52w - curr) / curr) * 100

                badge = "danger" if drawdown <= -20.0 else ("warning" if drawdown <= -8.0 else "info")
                status = "Deep Value Dip" if drawdown <= -20.0 else ("Correction Zone" if drawdown <= -8.0 else "Consolidation")

                stocks_list.append({
                    "symbol": sym.replace(".NS", ""),
                    "raw_symbol": sym,
                    "name": meta["name"],
                    "sector": meta["sector"],
                    "price": round(curr, 2),
                    "change": round(change, 2),
                    "pct_change": round(pct_change, 2),
                    "high_52w": round(high_52w, 2),
                    "drawdown_52w": round(drawdown, 2),
                    "recovery_upside_pct": round(upside, 2),
                    "status": status,
                    "badge": badge
                })
        except Exception as e:
            print(f"Stock {sym} err:", e)

    return jsonify({
        "timestamp": datetime.datetime.now().strftime("%d %b %Y, %I:%M %p IST"),
        "config": cfg,
        "nifty": nifty_data,
        "funds": funds_list,
        "stocks": stocks_list
    })

@app.route("/api/scan_nifty100", methods=["GET"])
def api_scan_nifty100():
    try:
        opps = scanner.scan_nifty_100(threshold_pct=-2.0)
        return jsonify({"success": True, "opportunities": opps, "count": len(opps)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/send_test_alert", methods=["POST"])
def api_send_test_alert():
    try:
        import send_email
        send_email.send_daily_email()
        return jsonify({"success": True, "message": "Email alert dispatched to meksmod1@gmail.com!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/")
def index():
    with open("interactive_portfolio_app.html", "r") as f:
        return f.read()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
