"""Shared market data layer for the Flask dashboard and the Streamlit app.

Also provides per-user helpers: instrument search (used by the "+ Add"
watchlist modal) and live holdings valuation (used by the My Portfolio tab
and the per-user email digest).
"""
import os
import re
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


def collect_market_data(cfg=None):
    """Fetch nifty + all funds + all stocks concurrently. Falls back to demo
    data (flagged) when the live feeds are unreachable.

    cfg: optional config dict in the DEFAULT_CONFIG shape ({"funds": {...},
    "stocks": {...}}). Pass a per-user watchlist cfg to personalise the
    dashboard; when omitted, the global user_config.json / DEFAULT_CONFIG is
    used (the shared single-profile view). An empty cfg (user with an empty
    watchlist) returns empty lists — the demo-fill logic never injects
    instruments the user did not configure.
    """
    cfg = cfg if cfg is not None else load_config()
    cfg_funds = cfg.get("funds") or {}
    cfg_stocks = cfg.get("stocks") or {}

    with ThreadPoolExecutor(max_workers=8) as pool:
        fut_nifty = pool.submit(_nifty_payload)
        fut_funds = {pool.submit(_fund_payload, code, meta): code for code, meta in cfg_funds.items()}
        fut_stocks = {pool.submit(_stock_payload, sym, meta): sym for sym, meta in cfg_stocks.items()}

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
    if not live and (cfg_funds or cfg_stocks):
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


# ---------------------------------------------------------------------------
# Holdings valuation (My Portfolio tab + per-user digest)
# ---------------------------------------------------------------------------

def _quote_stock(sym):
    """Lightweight live quote for one NSE symbol: price + day change."""
    tk = yf.Ticker(sym)
    hist = tk.history(period="5d")
    if hist.empty or len(hist) < 2:
        return None
    curr = float(hist['Close'].iloc[-1])
    prev = float(hist['Close'].iloc[-2])
    change = curr - prev
    return {
        "price": round(curr, 2),
        "change": round(change, 2),
        "pct_change": round((change / prev) * 100, 2),
        "date": hist.index[-1].strftime('%d %b %Y'),
    }


def _quote_fund(code):
    """Lightweight live quote for one AMFI scheme code: NAV + day change."""
    r = requests.get(f"https://api.mfapi.in/mf/{code}", timeout=8)
    if r.status_code != 200:
        return None
    nav_list = r.json().get("data", [])
    if len(nav_list) < 2:
        return None
    curr = float(nav_list[0]["nav"])
    prev = float(nav_list[1]["nav"])
    change = curr - prev
    return {
        "price": round(curr, 2),
        "change": round(change, 2),
        "pct_change": round((change / prev) * 100, 2),
        "date": nav_list[0]["date"],
    }


def collect_holdings_valuation(holdings):
    """Value a user's holding lots against live quotes.

    holdings: list of dicts from user_db.holdings_list().
    Returns {"holdings": [...valued lots...], "totals": {...}}.
    When a quote is unreachable the lot is valued at its buy price and
    flagged live=False so the UI can show "—" for the day change.
    """
    if not holdings:
        return {
            "holdings": [],
            "totals": {"invested": 0, "current_value": 0, "day_change": 0,
                       "day_pct": 0, "pnl": 0, "pnl_pct": 0, "live": True},
            "as_of": None,
        }

    def value_one(h):
        try:
            q = _quote_fund(h["symbol"]) if h["kind"] == "funds" else _quote_stock(h["symbol"])
        except Exception:
            q = None
        live = q is not None
        price = q["price"] if live else float(h["buy_price"])
        qty = float(h["qty"])
        current_value = round(price * qty, 2)
        cost = round(float(h["buy_price"]) * qty, 2)
        pnl = round(current_value - cost, 2)
        pnl_pct = round((pnl / cost) * 100, 2) if cost else 0.0
        return {
            "id": h["id"],
            "kind": h["kind"],
            "symbol": h["symbol"],
            "name": h["name"] or h["symbol"],
            "qty": qty,
            "buy_price": round(float(h["buy_price"]), 2),
            "buy_date": h.get("buy_date"),
            "current_price": price,
            "current_value": current_value,
            "day_change": q["change"] if live else None,
            "day_pct": q["pct_change"] if live else None,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "live": live,
        }

    valued = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(value_one, h) for h in holdings]
        for fut in as_completed(futs, timeout=45):
            try:
                valued.append(fut.result())
            except Exception:
                continue

    invested = round(sum(v["buy_price"] * v["qty"] for v in valued), 2)
    current_value = round(sum(v["current_value"] for v in valued), 2)
    day_change = round(sum((v["day_change"] or 0) * v["qty"] for v in valued), 2)
    day_pct = round((day_change / (current_value - day_change)) * 100, 2) if current_value != day_change else 0.0
    pnl = round(current_value - invested, 2)
    pnl_pct = round((pnl / invested) * 100, 2) if invested else 0.0

    return {
        "holdings": valued,
        "totals": {
            "invested": invested,
            "current_value": current_value,
            "day_change": day_change,
            "day_pct": day_pct,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "live": any(v["live"] for v in valued),
        },
        "as_of": datetime.datetime.now().strftime("%d %b %Y, %I:%M %p IST"),
    }


# ---------------------------------------------------------------------------
# Instrument search ("+ Add" modal — any NSE stock or mutual fund)
# ---------------------------------------------------------------------------

# Bundled catalog so search works even before the first AMFI master download:
# the 9 flagship funds + a few extras already referenced by this project.
STATIC_FUNDS = [
    {"code": "119783", "name": "SBI Healthcare Opportunities Fund (Direct-Growth)", "category": "Sectoral - Healthcare"},
    {"code": "113049", "name": "HDFC Gold ETF Fund", "category": "Commodities - Gold"},
    {"code": "119788", "name": "SBI Gold Fund (Direct-Growth)", "category": "Commodities - Gold"},
    {"code": "118551", "name": "Franklin U.S. Opportunities Equity Active FoF (Direct-Growth)", "category": "International Equity"},
    {"code": "118736", "name": "Nippon India Balanced Advantage Fund (Direct-Growth)", "category": "Hybrid Dynamic Asset Allocation"},
    {"code": "118778", "name": "Nippon India Small Cap Fund (Direct-Growth)", "category": "Equity - Small Cap"},
    {"code": "147662", "name": "ICICI Prudential Commodities Fund (Direct-Growth)", "category": "Thematic - Commodities"},
    {"code": "120578", "name": "SBI Technology Opportunities Fund (Direct-Growth)", "category": "Sectoral - Technology"},
    {"code": "120594", "name": "ICICI Prudential Technology Fund (Direct-Growth)", "category": "Sectoral - Technology"},
    {"code": "120716", "name": "UTI Nifty 50 Index Fund (Direct-Growth)", "category": "Large Cap / Index"},
    {"code": "122639", "name": "Parag Parikh Flexi Cap Fund (Direct-Growth)", "category": "Flexi Cap Equity"},
    {"code": "118989", "name": "HDFC Top 100 Fund (Direct-Growth)", "category": "Large Cap Equity"},
]

AMFI_MASTER_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
AMFI_CACHE_FILE = os.path.join(BASE_DIR, "amfi_master_cache.json")
AMFI_CACHE_TTL = 24 * 3600  # refresh the ~3 MB master list once a day

try:
    import nifty100_intraday_scanner as _scanner_mod
    STATIC_STOCKS = [s for s in getattr(_scanner_mod, "NIFTY_100_STOCKS", []) if s.endswith(".NS")]
except Exception:
    STATIC_STOCKS = []


def _amfi_master():
    """AMFI full scheme list (code + name), cached on disk for 24h."""
    if os.path.exists(AMFI_CACHE_FILE):
        try:
            age = datetime.datetime.now().timestamp() - os.path.getmtime(AMFI_CACHE_FILE)
            if age < AMFI_CACHE_TTL:
                with open(AMFI_CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
    try:
        r = requests.get(AMFI_MASTER_URL, timeout=20)
        if r.status_code == 200 and r.text:
            schemes = []
            for line in r.text.splitlines():
                parts = line.split(";")
                if len(parts) >= 6 and parts[0].strip().isdigit() and parts[3].strip():
                    schemes.append({
                        "code": parts[0].strip(),
                        "name": parts[3].strip(),
                        "category": (parts[4].strip() or parts[5].strip() or "Mutual Fund"),
                    })
            with open(AMFI_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(schemes, f)
            return schemes
    except Exception:
        pass
    return None


def _search_funds(q, limit):
    ql = q.lower()
    results = {}

    def add(code, name, category="Mutual Fund"):
        if code in results:
            return
        results[code] = {"kind": "funds", "symbol": code, "name": name, "category": category}

    # 1) live AMFI master (cached) — richest source
    try:
        for s in (_amfi_master() or []):
            if ql in s["name"].lower() or ql in s["code"]:
                add(s["code"], s["name"], s.get("category", "Mutual Fund"))
                if len(results) >= limit * 2:
                    break
    except Exception:
        pass
    # 2) mfapi search endpoint (community API) as a live alternative
    if len(results) < limit:
        try:
            r = requests.get(f"https://api.mfapi.in/mf/search?q={q}", timeout=10)
            if r.status_code == 200:
                for s in (r.json() or [])[:limit]:
                    add(str(s.get("schemeCode", "")), s.get("schemeName", ""), "Mutual Fund")
        except Exception:
            pass
    # 3) bundled catalog (works offline)
    if len(results) < limit:
        for s in STATIC_FUNDS:
            if ql in s["name"].lower() or ql in s["code"]:
                add(s["code"], s["name"], s["category"])
    return list(results.values())[:limit]


def _search_stocks(q, limit):
    ql = q.lower().replace(".ns", "")
    results = {}

    def add(raw_sym, name="", sector=""):
        sym = raw_sym.upper().rstrip(".NS") if raw_sym.upper().endswith(".NS") else raw_sym.upper()
        key = f"{sym}.NS"
        if key in results:
            return
        results[key] = {
            "kind": "stocks",
            "symbol": key,
            "name": name or f"{sym} Ltd",
            "sector": sector or "NSE",
        }

    for s in STATIC_STOCKS:
        if ql in s.lower():
            add(s)

    # live Yahoo search enriches with real company names when reachable
    if len(results) < limit:
        try:
            for r in (yf.Search(q, max_results=limit).quotes or []):
                sym = r.get("symbol", "")
                if sym.endswith(".NS"):
                    add(sym, r.get("shortname") or r.get("longname") or "", "NSE")
        except Exception:
            pass

    return list(results.values())[:limit]


def search_instruments(q, limit=12):
    """Search NSE stocks and mutual funds for the "+ Add" modal."""
    q = (q or "").strip()
    if not q:
        return {"stocks": [], "funds": []}
    return {
        "stocks": _search_stocks(q, limit),
        "funds": _search_funds(q, limit),
    }
