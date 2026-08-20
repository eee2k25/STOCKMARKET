"""Shared market data layer for the Flask dashboard and the Streamlit app."""
import os
import json
import math
import random
import datetime
import requests
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "user_config.json")
TEMPLATE_FILE = os.path.join(BASE_DIR, "interactive_portfolio_app.html")

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


# ---------------------------------------------------------------------------
# Data fetching (parallel + cached, with graceful demo fallback)
# ---------------------------------------------------------------------------

def _walk_back(end, n, vol, seed):
    """Generate a plausible price walk that ends exactly at `end`."""
    rng = random.Random(seed)
    pts = [float(end)]
    for _ in range(n - 1):
        pts.append(pts[-1] * (1 + rng.uniform(-vol, vol)))
    return [round(p, 2) for p in reversed(pts)]


def _biz_dates(n):
    """Last n business-day labels, oldest first."""
    d = datetime.date.today()
    out = []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.strftime('%d %b %y'))
        d -= datetime.timedelta(days=1)
    return list(reversed(out))


def _fund_payload(code, meta):
    r = requests.get(f"https://api.mfapi.in/mf/{code}", timeout=8)
    if r.status_code != 200:
        return None
    data = r.json()
    nav_list = data.get("data", [])
    if len(nav_list) < 2:
        return None
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

    return {
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
        "badge": badge,
        "spark": [round(float(x["nav"]), 2) for x in nav_list[:60][::-1]],
        "spark_dates": [x["date"] for x in nav_list[:60][::-1]]
    }


def _stock_payload(sym, meta):
    tk = yf.Ticker(sym)
    hist = tk.history(period="1y")
    if hist.empty or len(hist) < 2:
        return None
    curr = float(hist['Close'].iloc[-1])
    prev = float(hist['Close'].iloc[-2])
    high_52w = float(hist['High'].max())
    change = curr - prev
    pct_change = (change / prev) * 100
    drawdown = ((curr - high_52w) / high_52w) * 100
    upside = ((high_52w - curr) / curr) * 100

    badge = "danger" if drawdown <= -20.0 else ("warning" if drawdown <= -8.0 else "info")
    status = "Deep Value Dip" if drawdown <= -20.0 else ("Correction Zone" if drawdown <= -8.0 else "Consolidation")

    tail = hist.tail(60)
    return {
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
        "badge": badge,
        "spark": [round(float(x), 2) for x in tail['Close'].tolist()],
        "spark_dates": [d.strftime('%d %b %y') for d in tail.index]
    }


def _nifty_payload():
    nifty_data = {"symbol": "NIFTY 50", "price": 24244.15, "change": -121.85,
                  "pct_change": -0.50, "high_52w": 26277.35, "spark": [], "spark_dates": []}
    tk = yf.Ticker("^NSEI")
    hist = tk.history(period="3mo")
    if hist.empty or len(hist) < 2:
        return None
    curr = float(hist['Close'].iloc[-1])
    prev = float(hist['Close'].iloc[-2])
    tail = hist.tail(60)
    spark = [round(float(x), 2) for x in tail['Close'].tolist()]
    nifty_data = {
        "symbol": "NIFTY 50",
        "price": round(curr, 2),
        "change": round(curr - prev, 2),
        "pct_change": round(((curr - prev) / prev) * 100, 2),
        "high_52w": round(float(hist['High'].max()), 2),
        "spark": spark,
        "spark_dates": [d.strftime('%d %b %y') for d in tail.index]
    }
    return nifty_data


def _demo_data(cfg):
    """Realistic sample data used when live feeds are unreachable, so the
    dashboard stays fully usable (clearly flagged as demo in the UI)."""
    rng = random.Random(42)

    def wave(i, amp):
        return math.sin(i / 3.1) * amp + math.sin(i / 1.3) * (amp / 3)

    dates = _biz_dates(60)
    spark = _walk_back(24244.15, 60, 0.009, 7)
    nifty = {
        "symbol": "NIFTY 50", "price": 24244.15, "change": -121.85,
        "pct_change": -0.50, "high_52w": 26277.35,
        "spark": spark, "spark_dates": dates
    }

    funds = []
    for i, (code, meta) in enumerate(cfg["funds"].items()):
        nav = round(95 + rng.random() * 120, 2)
        dd = round(-(rng.random() * 16) - 1.0, 2)
        high = round(nav / (1 + dd / 100), 2)
        chg = round(rng.uniform(-1.2, 0.9), 2)
        badge = "danger" if dd <= -10 else ("warning" if dd <= -4 else "success")
        status = "High Conviction Dip" if dd <= -10 else ("Value Pullback" if dd <= -4 else "Holding Support")
        funds.append({
            "code": code, "name": meta["name"], "category": meta["category"],
            "rating": meta.get("rating", "4★"), "nav": nav, "date": "—",
            "change": chg, "pct_change": round(chg / nav * 100, 2),
            "high_52w": high, "drawdown_52w": dd,
            "recovery_upside_pct": round(-dd, 2), "status": status, "badge": badge,
            "spark": _walk_back(nav, 60, 0.011, 100 + i), "spark_dates": dates
        })

    stocks = []
    for j, (sym, meta) in enumerate(cfg["stocks"].items()):
        price = round(420 + rng.random() * 2600, 2)
        dd = round(-(rng.random() * 26) - 1.5, 2)
        high = round(price / (1 + dd / 100), 2)
        chg_pct = round(rng.uniform(-2.4, 1.6), 2)
        badge = "danger" if dd <= -20 else ("warning" if dd <= -8 else "info")
        status = "Deep Value Dip" if dd <= -20 else ("Correction Zone" if dd <= -8 else "Consolidation")
        stocks.append({
            "symbol": sym.replace(".NS", ""), "raw_symbol": sym, "name": meta["name"],
            "sector": meta["sector"], "price": price,
            "change": round(price * chg_pct / 100, 2), "pct_change": chg_pct,
            "high_52w": high, "drawdown_52w": dd,
            "recovery_upside_pct": round(-dd, 2), "status": status, "badge": badge,
            "spark": _walk_back(price, 60, 0.015, 200 + j), "spark_dates": dates
        })

    return nifty, funds, stocks


def collect_market_data():
    """Fetch nifty + all funds + all stocks concurrently. Falls back to demo
    data (flagged) when the live feeds are unreachable."""
    cfg = load_config()

    with ThreadPoolExecutor(max_workers=8) as pool:
        fut_nifty = pool.submit(_nifty_payload)
        fut_funds = {pool.submit(_fund_payload, code, meta): code for code, meta in cfg["funds"].items()}
        fut_stocks = {pool.submit(_stock_payload, sym, meta): sym for sym, meta in cfg["stocks"].items()}

        try:
            nifty = fut_nifty.result(timeout=20)
        except Exception:
            nifty = None

        funds_list, funds_failed = [], 0
        for fut in as_completed(fut_funds, timeout=30):
            try:
                res = fut.result()
            except Exception:
                res = None
            if res:
                funds_list.append(res)
            else:
                funds_failed += 1

        stocks_list, stocks_failed = [], 0
        for fut in as_completed(fut_stocks, timeout=30):
            try:
                res = fut.result()
            except Exception:
                res = None
            if res:
                stocks_list.append(res)
            else:
                stocks_failed += 1

    live = nifty is not None and funds_list and stocks_list and funds_failed == 0 and stocks_failed == 0
    demo = False
    if not live:
        # Partial or total feed failure -> serve demo snapshot so the UI stays usable.
        demo = True
        d_nifty, d_funds, d_stocks = _demo_data(cfg)
        if nifty is None:
            nifty = d_nifty
        if funds_failed:
            have = {f["code"] for f in funds_list}
            funds_list += [f for f in d_funds if f["code"] not in have]
        if stocks_failed:
            have = {s["symbol"] for s in stocks_list}
            stocks_list += [s for s in d_stocks if s["symbol"] not in have]

    return {
        "timestamp": datetime.datetime.now().strftime("%d %b %Y, %I:%M %p IST"),
        "config": cfg,
        "nifty": nifty,
        "funds": funds_list,
        "stocks": stocks_list,
        "demo": demo
    }
