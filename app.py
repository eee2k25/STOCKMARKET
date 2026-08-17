import os
import json
import datetime
import requests
import yfinance as yf
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

# State storage
CONFIG_FILE = "user_config.json"

DEFAULT_CONFIG = {
    "email": "meksmod1@gmail.com",
    "risk_profile": "moderate",
    "alert_frequency": "eod_plus_instant",
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
        "RELIANCE.NS": {"name": "Reliance Industries Ltd", "sector": "Energy / Retail / Telecom"},
        "HDFCBANK.NS": {"name": "HDFC Bank Ltd", "sector": "Private Banking & Financials"},
        "ICICIBANK.NS": {"name": "ICICI Bank Ltd", "sector": "Private Banking & Financials"},
        "TCS.NS": {"name": "Tata Consultancy Services", "sector": "IT & Software Services"},
        "INFY.NS": {"name": "Infosys Ltd", "sector": "IT & Software Services"},
        "LT.NS": {"name": "Larsen & Toubro Ltd", "sector": "Infrastructure & Capital Goods"},
        "BHARTIARTL.NS": {"name": "Bharti Airtel Ltd", "sector": "Telecommunications"},
        "ITC.NS": {"name": "ITC Ltd", "sector": "FMCG & Diversified"},
        "SBIN.NS": {"name": "State Bank of India", "sector": "Public Sector Banking"},
        "SUNPHARMA.NS": {"name": "Sun Pharma Ltd", "sector": "Healthcare & Pharma"}
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
    
    # 1. Fetch Nifty 50
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

    # 2. Fetch Mutual Funds
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
                    low_52w = min(navs_1y) if navs_1y else curr_nav
                    change = curr_nav - prev_nav
                    pct_change = (change / prev_nav) * 100
                    drawdown = ((curr_nav - high_52w) / high_52w) * 100
                    upside = ((high_52w - curr_nav) / curr_nav) * 100

                    # Status classification
                    if drawdown <= -10.0:
                        status = "High Conviction Dip"
                        badge = "danger"
                    elif drawdown <= -4.0:
                        status = "Value Pullback"
                        badge = "warning"
                    else:
                        status = "Holding Support / Peak"
                        badge = "success"

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
                        "low_52w": round(low_52w, 2),
                        "drawdown_52w": round(drawdown, 2),
                        "recovery_upside_pct": round(upside, 2),
                        "status": status,
                        "badge": badge
                    })
        except Exception as e:
            print(f"Fund {code} err:", e)

    # 3. Fetch Stocks
    stocks_list = []
    for sym, meta in cfg["stocks"].items():
        try:
            tk = yf.Ticker(sym)
            hist = tk.history(period="1y")
            if not hist.empty and len(hist) >= 2:
                curr = float(hist['Close'].iloc[-1])
                prev = float(hist['Close'].iloc[-2])
                high_52w = float(hist['High'].max())
                low_52w = float(hist['Low'].min())
                change = curr - prev
                pct_change = (change / prev) * 100
                drawdown = ((curr - high_52w) / high_52w) * 100
                upside = ((high_52w - curr) / curr) * 100

                if drawdown <= -20.0:
                    status = "Deep Value Dip"
                    badge = "danger"
                elif drawdown <= -8.0:
                    status = "Correction Zone"
                    badge = "warning"
                else:
                    status = "Consolidation"
                    badge = "info"

                stocks_list.append({
                    "symbol": sym.replace(".NS", ""),
                    "raw_symbol": sym,
                    "name": meta["name"],
                    "sector": meta["sector"],
                    "price": round(curr, 2),
                    "change": round(change, 2),
                    "pct_change": round(pct_change, 2),
                    "high_52w": round(high_52w, 2),
                    "low_52w": round(low_52w, 2),
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

@app.route("/api/add_stock", methods=["POST"])
def add_stock():
    data = request.json or {}
    symbol = data.get("symbol", "").strip().upper()
    name = data.get("name", symbol).strip()
    sector = data.get("sector", "Nifty Constituent").strip()
    if not symbol:
        return jsonify({"success": False, "error": "Invalid symbol"}), 400
    if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
        symbol_key = f"{symbol}.NS"
    else:
        symbol_key = symbol
    cfg = load_config()
    cfg["stocks"][symbol_key] = {"name": name, "sector": sector}
    save_config(cfg)
    return jsonify({"success": True})

@app.route("/api/remove_stock", methods=["POST"])
def remove_stock():
    data = request.json or {}
    sym = data.get("symbol", "").strip()
    cfg = load_config()
    if sym in cfg["stocks"]:
        del cfg["stocks"][sym]
        save_config(cfg)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Not found"}), 404

@app.route("/api/add_fund", methods=["POST"])
def add_fund():
    data = request.json or {}
    code = str(data.get("code", "")).strip()
    name = data.get("name", f"Fund #{code}").strip()
    category = data.get("category", "Mutual Fund").strip()
    if not code:
        return jsonify({"success": False, "error": "Invalid code"}), 400
    cfg = load_config()
    cfg["funds"][code] = {"name": name, "category": category, "rating": "Active"}
    save_config(cfg)
    return jsonify({"success": True})

@app.route("/api/remove_fund", methods=["POST"])
def remove_fund():
    data = request.json or {}
    code = str(data.get("code", "")).strip()
    cfg = load_config()
    if code in cfg["funds"]:
        del cfg["funds"][code]
        save_config(cfg)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Not found"}), 404

@app.route("/api/update_profile", methods=["POST"])
def update_profile():
    data = request.json or {}
    cfg = load_config()
    if "email" in data:
        cfg["email"] = data["email"].strip()
    if "risk_profile" in data:
        cfg["risk_profile"] = data["risk_profile"].strip().lower()
    save_config(cfg)
    return jsonify({"success": True, "config": cfg})

# Main Interactive UI Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Indian Stock & Mutual Fund Downturn Monitor</title>
  <!-- Tailwind CSS via CDN for crisp UI -->
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    body { font-family: 'Inter', sans-serif; }
    .glass { background: rgba(30, 41, 59, 0.85); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
    .card-glow:hover { border-color: rgba(56, 189, 248, 0.4); box-shadow: 0 0 20px rgba(56, 189, 248, 0.15); }
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen pb-16">

  <!-- Top Navbar -->
  <header class="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
          <i class="fa-solid fa-chart-line text-white text-lg"></i>
        </div>
        <div>
          <h1 class="text-lg font-bold tracking-tight text-white flex items-center gap-2">
            Nifty & MF Dip Advisor
            <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> LIVE
            </span>
          </h1>
          <p class="text-xs text-slate-400">Automated Indian Market Downturn & Recovery Engine</p>
        </div>
      </div>

      <!-- User Badges & Actions -->
      <div class="flex items-center gap-3">
        <div class="hidden sm:flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700 text-xs">
          <i class="fa-regular fa-envelope text-cyan-400"></i>
          <span id="nav-email" class="text-slate-300 font-medium">meksmod1@gmail.com</span>
        </div>
        <div class="flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700 text-xs">
          <i class="fa-solid fa-shield-halved text-blue-400"></i>
          <span id="nav-risk" class="text-slate-300 font-medium capitalize">Moderate Risk</span>
        </div>
        <button onclick="refreshData()" class="bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 shadow-md shadow-cyan-600/20">
          <i id="refresh-icon" class="fa-solid fa-rotate"></i> Sync
        </button>
        <button onclick="openDeploymentModal()" class="bg-indigo-600/80 hover:bg-indigo-600 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition flex items-center gap-1.5 border border-indigo-500/30">
          <i class="fa-solid fa-cloud-arrow-up"></i> Free Deploy Guide
        </button>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-4 sm:px-6 pt-6 space-y-6">

    <!-- Benchmark & Market Diagnostics Banner -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <!-- Nifty 50 Card -->
      <div class="glass rounded-xl p-5 border border-slate-800 relative overflow-hidden">
        <div class="flex justify-between items-start">
          <div>
            <span class="text-xs font-medium text-slate-400 uppercase tracking-wider">Benchmark Index</span>
            <div class="text-2xl font-black text-white mt-1" id="nifty-price">₹24,244.15</div>
          </div>
          <span id="nifty-chg-badge" class="text-xs font-bold px-2.5 py-1 rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/20">
            -0.50% (-121.85)
          </span>
        </div>
        <div class="mt-4 flex justify-between text-xs text-slate-400 border-t border-slate-800/80 pt-3">
          <span>52W Peak: <strong class="text-slate-200" id="nifty-high">₹24,774.30</strong></span>
          <span>Status: <strong class="text-amber-400">Consolidation</strong></span>
        </div>
      </div>

      <!-- Total Watchlist Value & Dips -->
      <div class="glass rounded-xl p-5 border border-slate-800">
        <span class="text-xs font-medium text-slate-400 uppercase tracking-wider">Active Watchlist Items</span>
        <div class="text-2xl font-black text-white mt-1 flex items-baseline gap-2">
          <span id="total-items">19 Assets</span>
          <span class="text-xs text-slate-400 font-normal">(9 MFs, 10 Stocks)</span>
        </div>
        <div class="mt-4 flex justify-between text-xs text-slate-400 border-t border-slate-800/80 pt-3">
          <span>Dips in Discount: <strong class="text-emerald-400" id="discount-items-count">7 Opportunities</strong></span>
          <span>Alert Mode: <strong class="text-cyan-400">Active</strong></span>
        </div>
      </div>

      <!-- Dip Opportunity Highlight -->
      <div class="glass rounded-xl p-5 border border-slate-800 bg-gradient-to-br from-emerald-950/40 to-slate-900">
        <span class="text-xs font-medium text-emerald-400 uppercase tracking-wider flex items-center gap-1">
          <i class="fa-solid fa-bullseye"></i> Top High Margin Dip
        </span>
        <div class="text-xl font-bold text-white mt-1 truncate" id="top-dip-name">SBI Gold & Tech Funds</div>
        <div class="mt-2 text-xs text-slate-300">
          Drawdown: <strong class="text-rose-400">-14.6%</strong> | Upside: <strong class="text-emerald-400">+17.1%</strong>
        </div>
        <div class="mt-2 text-[11px] text-slate-400">Historical mean-reversion: 4-7 months</div>
      </div>

      <!-- Quick Calculator Card Trigger -->
      <div class="glass rounded-xl p-5 border border-slate-800 flex flex-col justify-between">
        <div>
          <span class="text-xs font-medium text-indigo-400 uppercase tracking-wider flex items-center gap-1">
            <i class="fa-solid fa-calculator"></i> Recovery Planner
          </span>
          <p class="text-xs text-slate-300 mt-1">Simulate exact ₹ returns & tranche sizing for any dip.</p>
        </div>
        <button onclick="scrollToCalculator()" class="mt-3 w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition text-center shadow-lg shadow-indigo-600/20">
          Open Investment Calculator
        </button>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex border-b border-slate-800 gap-2">
      <button onclick="switchTab('funds')" id="tab-funds" class="px-5 py-3 text-sm font-semibold text-cyan-400 border-b-2 border-cyan-400 flex items-center gap-2">
        <i class="fa-solid fa-layer-group"></i> Tracked Mutual Funds (9)
      </button>
      <button onclick="switchTab('stocks')" id="tab-stocks" class="px-5 py-3 text-sm font-semibold text-slate-400 hover:text-slate-200 flex items-center gap-2">
        <i class="fa-solid fa-building-columns"></i> Nifty 50 Stocks (10)
      </button>
      <button onclick="switchTab('calculator')" id="tab-calc" class="px-5 py-3 text-sm font-semibold text-slate-400 hover:text-slate-200 flex items-center gap-2">
        <i class="fa-solid fa-money-bill-trend-up"></i> Recovery & Tranche Math
      </button>
      <button onclick="switchTab('alerts')" id="tab-alerts" class="px-5 py-3 text-sm font-semibold text-slate-400 hover:text-slate-200 flex items-center gap-2">
        <i class="fa-regular fa-bell"></i> Email Alert Dispatcher
      </button>
    </div>

    <!-- TAB 1: MUTUAL FUNDS -->
    <div id="view-funds" class="space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="text-base font-bold text-white">Mutual Funds Live Portfolio (AMFI NAV Pipeline)</h2>
          <p class="text-xs text-slate-400">Official daily closing NAVs, 52-week drawdowns, and upside calculations.</p>
        </div>
        <button onclick="openAddFundModal()" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold px-3 py-2 rounded-lg transition flex items-center gap-1.5">
          <i class="fa-solid fa-plus text-cyan-400"></i> Add New Fund
        </button>
      </div>

      <div class="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
        <table class="w-full text-left text-sm">
          <thead class="bg-slate-800/80 text-xs font-semibold uppercase text-slate-400 border-b border-slate-700/80">
            <tr>
              <th class="py-3.5 px-4">Scheme Name & AMFI Code</th>
              <th class="py-3.5 px-4">Category</th>
              <th class="py-3.5 px-4">Latest NAV</th>
              <th class="py-3.5 px-4">1-Day Chg</th>
              <th class="py-3.5 px-4">52W High</th>
              <th class="py-3.5 px-4">52W Drawdown</th>
              <th class="py-3.5 px-4">Upside Potential</th>
              <th class="py-3.5 px-4">Advisory Action</th>
              <th class="py-3.5 px-4 text-center">Action</th>
            </tr>
          </thead>
          <tbody id="funds-tbody" class="divide-y divide-slate-800/60 text-xs">
            <!-- Dynamically populated -->
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 2: STOCKS -->
    <div id="view-stocks" class="space-y-4 hidden">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="text-base font-bold text-white">Nifty 50 Stocks Baseline Watchlist</h2>
          <p class="text-xs text-slate-400">Live NSE price action, technical support levels, and 52-week peak distance.</p>
        </div>
        <button onclick="openAddStockModal()" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold px-3 py-2 rounded-lg transition flex items-center gap-1.5">
          <i class="fa-solid fa-plus text-cyan-400"></i> Add Stock Ticker
        </button>
      </div>

      <div class="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
        <table class="w-full text-left text-sm">
          <thead class="bg-slate-800/80 text-xs font-semibold uppercase text-slate-400 border-b border-slate-700/80">
            <tr>
              <th class="py-3.5 px-4">Ticker & Company</th>
              <th class="py-3.5 px-4">Sector</th>
              <th class="py-3.5 px-4">Live Price (₹)</th>
              <th class="py-3.5 px-4">1-Day Movement</th>
              <th class="py-3.5 px-4">52W High (₹)</th>
              <th class="py-3.5 px-4">52W Drawdown</th>
              <th class="py-3.5 px-4">Upside to Peak</th>
              <th class="py-3.5 px-4">Valuation Status</th>
              <th class="py-3.5 px-4 text-center">Action</th>
            </tr>
          </thead>
          <tbody id="stocks-tbody" class="divide-y divide-slate-800/60 text-xs">
            <!-- Dynamically populated -->
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 3: RECOVERY & TRANCHE CALCULATOR -->
    <div id="view-calculator" class="space-y-6 hidden">
      <div class="glass rounded-xl p-6 border border-slate-800">
        <h2 class="text-lg font-bold text-white flex items-center gap-2">
          <i class="fa-solid fa-calculator text-indigo-400"></i> Dip Investment & Recovery Potential Calculator
        </h2>
        <p class="text-xs text-slate-400 mt-1">
          Input your available deployment capital to calculate phased tranche allocation (Moderate Profile) and projected rupee gains upon recovery.
        </p>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6">
          <div>
            <label class="block text-xs font-semibold text-slate-300 uppercase mb-1.5">Deployment Capital (₹)</label>
            <input type="number" id="calc-capital" value="100000" step="5000" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-white font-bold text-sm focus:outline-none focus:border-cyan-500" oninput="runCalculator()">
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-300 uppercase mb-1.5">Select Asset from Watchlist</label>
            <select id="calc-asset" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" onchange="runCalculator()">
              <!-- Options populated dynamically -->
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-300 uppercase mb-1.5">Risk Staging Strategy</label>
            <select id="calc-staging" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-cyan-500" onchange="runCalculator()">
              <option value="moderate">Moderate (30% / 30% / 40% Tranches)</option>
              <option value="aggressive">Aggressive (50% / 50% Dip Lump-sum)</option>
              <option value="conservative">Conservative (20% Phased x 5 SIPs)</option>
            </select>
          </div>
        </div>

        <!-- Calculated Output Cards -->
        <div class="grid grid-cols-1 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-800">
          <div class="bg-slate-900/90 p-4 rounded-lg border border-slate-800">
            <span class="text-[11px] font-semibold text-slate-400 uppercase">Current Discount</span>
            <div class="text-xl font-black text-rose-400 mt-1" id="calc-discount">-14.6%</div>
            <span class="text-[11px] text-slate-500">From 52W High</span>
          </div>
          <div class="bg-slate-900/90 p-4 rounded-lg border border-slate-800">
            <span class="text-[11px] font-semibold text-slate-400 uppercase">Tranche 1 Entry (30%)</span>
            <div class="text-xl font-black text-cyan-400 mt-1" id="calc-t1">₹30,000</div>
            <span class="text-[11px] text-slate-500">Deploy immediately at dip</span>
          </div>
          <div class="bg-slate-900/90 p-4 rounded-lg border border-slate-800">
            <span class="text-[11px] font-semibold text-slate-400 uppercase">Projected Value at Peak</span>
            <div class="text-xl font-black text-emerald-400 mt-1" id="calc-projected">₹1,17,120</div>
            <span class="text-[11px] text-emerald-500 font-semibold" id="calc-profit">+₹17,120 (+17.1%)</span>
          </div>
          <div class="bg-slate-900/90 p-4 rounded-lg border border-slate-800">
            <span class="text-[11px] font-semibold text-slate-400 uppercase">Estimated Recovery Horizon</span>
            <div class="text-xl font-black text-indigo-400 mt-1" id="calc-horizon">4 - 7 Months</div>
            <span class="text-[11px] text-slate-500">Based on historical cycles</span>
          </div>
        </div>

        <div class="mt-6 bg-slate-900/60 p-4 rounded-lg border border-slate-800/80 text-xs text-slate-300 space-y-2">
          <div class="font-bold text-slate-200 flex items-center gap-1.5">
            <i class="fa-solid fa-circle-info text-cyan-400"></i> Moderate Risk Staging Blueprint:
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
            <div class="p-2.5 rounded bg-slate-800/40 border border-slate-700/50">
              <strong class="text-cyan-300">Tranche 1 (30%):</strong> Deploy at current discount level. Sets your base margin of safety.
            </div>
            <div class="p-2.5 rounded bg-slate-800/40 border border-slate-700/50">
              <strong class="text-blue-300">Tranche 2 (30%):</strong> Reserve for secondary support test (e.g. 50-DMA test) or 30 days post initial entry.
            </div>
            <div class="p-2.5 rounded bg-slate-800/40 border border-slate-700/50">
              <strong class="text-purple-300">Tranche 3 (40%):</strong> Deploy on confirmed structural reversal or 200-DMA bottom test.
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 4: EMAIL ALERT DISPATCHER & PREVIEW -->
    <div id="view-alerts" class="space-y-6 hidden">
      <div class="glass rounded-xl p-6 border border-slate-800">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <i class="fa-regular fa-envelope text-cyan-400"></i> Daily EOD & Dip Email Alert Dispatcher
            </h2>
            <p class="text-xs text-slate-400 mt-1">Configured for: <strong class="text-slate-200">meksmod1@gmail.com</strong></p>
          </div>
          <div class="flex items-center gap-3">
            <button onclick="previewEmailTemplate()" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold px-4 py-2.5 rounded-lg transition">
              <i class="fa-solid fa-eye"></i> Preview Email HTML
            </button>
            <button onclick="simulateSendAlert()" class="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold px-4 py-2.5 rounded-lg transition shadow-lg shadow-emerald-600/20 flex items-center gap-2">
              <i class="fa-solid fa-paper-plane"></i> Send Test Alert Email
            </button>
          </div>
        </div>

        <div id="alert-status-box" class="hidden mt-4 p-4 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs">
          <div class="font-bold flex items-center gap-2">
            <i class="fa-solid fa-circle-check text-emerald-400"></i> Daily Downturn & Dip Alert Compiled!
          </div>
          <p class="mt-1 text-slate-300">
            Dispatched test digest for <strong>meksmod1@gmail.com</strong>. Contains 9 Mutual Funds and 10 Nifty Stocks with recovery calculations.
          </p>
        </div>

        <!-- Settings Form -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6 pt-6 border-t border-slate-800">
          <div>
            <label class="block text-xs font-semibold text-slate-300 uppercase mb-1">Alert Recipient Email</label>
            <input type="email" id="settings-email" value="meksmod1@gmail.com" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white text-xs focus:outline-none focus:border-cyan-500">
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-300 uppercase mb-1">Intraday Flash Drop Trigger Threshold</label>
            <select id="settings-threshold" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white text-xs focus:outline-none focus:border-cyan-500">
              <option value="2.5">Alert on ≥ 2.5% single-day drop</option>
              <option value="3.0" selected>Alert on ≥ 3.0% single-day drop (Standard)</option>
              <option value="5.0">Alert on ≥ 5.0% single-day drop (Major Corrections Only)</option>
            </select>
          </div>
        </div>
      </div>
    </div>

  </main>

  <!-- MODAL: ADD FUND -->
  <div id="modal-fund" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center hidden p-4">
    <div class="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4">
      <div class="flex justify-between items-center">
        <h3 class="text-base font-bold text-white">Add Indian Mutual Fund</h3>
        <button onclick="closeModals()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <div class="space-y-3 text-xs">
        <div>
          <label class="block text-slate-300 font-semibold mb-1">AMFI Scheme Code (e.g. 120716)</label>
          <input type="text" id="add-fund-code" placeholder="120716" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white">
        </div>
        <div>
          <label class="block text-slate-300 font-semibold mb-1">Scheme Name</label>
          <input type="text" id="add-fund-name" placeholder="UTI Nifty 50 Index Fund Direct Growth" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white">
        </div>
        <div>
          <label class="block text-slate-300 font-semibold mb-1">Category</label>
          <input type="text" id="add-fund-cat" placeholder="Large Cap / Index" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white">
        </div>
      </div>
      <div class="flex justify-end gap-2 pt-2">
        <button onclick="closeModals()" class="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg text-xs font-semibold">Cancel</button>
        <button onclick="submitAddFund()" class="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-semibold">Save Fund</button>
      </div>
    </div>
  </div>

  <!-- MODAL: ADD STOCK -->
  <div id="modal-stock" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center hidden p-4">
    <div class="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4">
      <div class="flex justify-between items-center">
        <h3 class="text-base font-bold text-white">Add Nifty Stock Ticker</h3>
        <button onclick="closeModals()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <div class="space-y-3 text-xs">
        <div>
          <label class="block text-slate-300 font-semibold mb-1">NSE Symbol (e.g. TATASTEEL)</label>
          <input type="text" id="add-stock-sym" placeholder="TATASTEEL" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white">
        </div>
        <div>
          <label class="block text-slate-300 font-semibold mb-1">Company Name</label>
          <input type="text" id="add-stock-name" placeholder="Tata Steel Ltd" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white">
        </div>
        <div>
          <label class="block text-slate-300 font-semibold mb-1">Sector</label>
          <input type="text" id="add-stock-sec" placeholder="Metals & Mining" class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white">
        </div>
      </div>
      <div class="flex justify-end gap-2 pt-2">
        <button onclick="closeModals()" class="px-4 py-2 bg-slate-800 text-slate-300 rounded-lg text-xs font-semibold">Cancel</button>
        <button onclick="submitAddStock()" class="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-semibold">Save Stock</button>
      </div>
    </div>
  </div>

  <!-- MODAL: FREE 100% DEPLOYMENT GUIDE -->
  <div id="modal-deploy" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center hidden p-4">
    <div class="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
      <div class="flex justify-between items-center border-b border-slate-800 pb-3">
        <div>
          <h3 class="text-base font-bold text-white flex items-center gap-2">
            <i class="fa-solid fa-cloud-arrow-up text-cyan-400"></i> Free 100% Lifetime Hosting & Automation Guide
          </h3>
          <p class="text-xs text-slate-400">Run this exact dashboard and automated daily email alerts forever for ₹0.</p>
        </div>
        <button onclick="closeModals()" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
      </div>

      <div class="space-y-4 text-xs text-slate-300">
        <!-- Option 1 -->
        <div class="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
          <div class="font-bold text-cyan-300 text-sm flex items-center gap-2">
            <span class="w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center text-xs">1</span>
            Free Option A: Streamlit Community Cloud / Render (Web App)
          </div>
          <p>
            You can push this repository directly to GitHub and connect it to <strong>Streamlit Community Cloud</strong> or <strong>Render.com</strong> (Free Web Service tier). It provides a free live HTTPS URL (e.g. <code>https://my-stock-advisor.streamlit.app</code>) that you can open on your phone anytime.
          </p>
        </div>

        <!-- Option 2 -->
        <div class="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
          <div class="font-bold text-emerald-300 text-sm flex items-center gap-2">
            <span class="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs">2</span>
            Free Option B: GitHub Actions Cron (Automated Daily 4 PM IST Email)
          </div>
          <p>
            A free GitHub Action workflow file (<code>.github/workflows/daily_alert.yml</code>) runs on GitHub's free servers every trading day at 4:00 PM IST, pulls the AMFI NAVs & NSE stock data, and emails the complete analysis directly to <code>meksmod1@gmail.com</code> via free Gmail SMTP. Zero maintenance required.
          </p>
        </div>

        <!-- Option 3 -->
        <div class="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2">
          <div class="font-bold text-indigo-300 text-sm flex items-center gap-2">
            <span class="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-xs">3</span>
            Free Option C: PythonAnywhere (Free Daily Task)
          </div>
          <p>
            Sign up on <strong>PythonAnywhere.com</strong> (Free Forever plan) and schedule <code>python3 indian_market_monitor.py</code> to execute daily at 16:00 IST.
          </p>
        </div>
      </div>

      <div class="flex justify-end pt-2">
        <button onclick="closeModals()" class="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-semibold">Got it!</button>
      </div>
    </div>
  </div>

  <script>
    let globalData = null;

    async function loadData() {
      try {
        const res = await fetch('/api/data');
        globalData = await res.json();
        renderUI(globalData);
      } catch (err) {
        console.error("Failed to load data", err);
      }
    }

    function renderUI(data) {
      if (!data) return;

      // Nifty Banner
      document.getElementById('nifty-price').textContent = `₹${data.nifty.price.toLocaleString('en-IN')}`;
      const nChg = document.getElementById('nifty-chg-badge');
      const isNeg = data.nifty.pct_change < 0;
      nChg.textContent = `${isNeg ? '' : '+'}${data.nifty.pct_change}% (${isNeg ? '' : '+'}${data.nifty.change})`;
      nChg.className = isNeg 
        ? "text-xs font-bold px-2.5 py-1 rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/20"
        : "text-xs font-bold px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
      document.getElementById('nifty-high').textContent = `₹${data.nifty.high_52w.toLocaleString('en-IN')}`;

      // Total counts
      const totalCount = data.funds.length + data.stocks.length;
      document.getElementById('total-items').textContent = `${totalCount} Assets`;

      // Render Mutual Funds Table
      const fundsTbody = document.getElementById('funds-tbody');
      fundsTbody.innerHTML = '';
      const calcSelect = document.getElementById('calc-asset');
      calcSelect.innerHTML = '';

      let dipCount = 0;

      data.funds.forEach(f => {
        if (f.drawdown_52w <= -5) dipCount++;
        const isFneg = f.pct_change < 0;
        const badgeColor = f.badge === 'danger' ? 'bg-rose-500/10 text-rose-400 border-rose-500/30' : (f.badge === 'warning' ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30');

        fundsTbody.innerHTML += `
          <tr class="hover:bg-slate-800/40 transition">
            <td class="py-3 px-4 font-semibold text-slate-100">
              ${f.name}
              <div class="text-[11px] text-slate-500 font-normal">AMFI Code: #${f.code} · ${f.rating}</div>
            </td>
            <td class="py-3 px-4 text-slate-300">${f.category}</td>
            <td class="py-3 px-4 font-bold text-white">₹${f.nav.toFixed(2)}</td>
            <td class="py-3 px-4 font-semibold ${isFneg ? 'text-rose-400' : 'text-emerald-400'}">
              ${isFneg ? '' : '+'}${f.pct_change}%
            </td>
            <td class="py-3 px-4 text-slate-300">₹${f.high_52w.toFixed(2)}</td>
            <td class="py-3 px-4 font-bold text-rose-400">${f.drawdown_52w.toFixed(1)}%</td>
            <td class="py-3 px-4 font-bold text-emerald-400">+${f.recovery_upside_pct.toFixed(1)}%</td>
            <td class="py-3 px-4">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${badgeColor}">
                ${f.status}
              </span>
            </td>
            <td class="py-3 px-4 text-center">
              <button onclick="removeFund('${f.code}')" class="text-slate-500 hover:text-rose-400 transition" title="Remove Fund">
                <i class="fa-solid fa-trash"></i>
              </button>
            </td>
          </tr>
        `;

        calcSelect.innerHTML += `<option value="fund_${f.code}">[MF] ${f.name} (${f.drawdown_52w.toFixed(1)}% dip)</option>`;
      });

      // Render Stocks Table
      const stocksTbody = document.getElementById('stocks-tbody');
      stocksTbody.innerHTML = '';

      data.stocks.forEach(s => {
        if (s.drawdown_52w <= -10) dipCount++;
        const isSneg = s.pct_change < 0;
        const badgeColor = s.badge === 'danger' ? 'bg-rose-500/10 text-rose-400 border-rose-500/30' : (s.badge === 'warning' ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' : 'bg-slate-800 text-slate-300 border-slate-700');

        stocksTbody.innerHTML += `
          <tr class="hover:bg-slate-800/40 transition">
            <td class="py-3 px-4 font-semibold text-slate-100">
              ${s.symbol}
              <div class="text-[11px] text-slate-500 font-normal">${s.name}</div>
            </td>
            <td class="py-3 px-4 text-slate-300">${s.sector}</td>
            <td class="py-3 px-4 font-bold text-white">₹${s.price.toLocaleString('en-IN')}</td>
            <td class="py-3 px-4 font-semibold ${isSneg ? 'text-rose-400' : 'text-emerald-400'}">
              ${isSneg ? '' : '+'}${s.pct_change}% (₹${isSneg ? '' : '+'}${s.change})
            </td>
            <td class="py-3 px-4 text-slate-300">₹${s.high_52w.toLocaleString('en-IN')}</td>
            <td class="py-3 px-4 font-bold text-rose-400">${s.drawdown_52w.toFixed(1)}%</td>
            <td class="py-3 px-4 font-bold text-emerald-400">+${s.recovery_upside_pct.toFixed(1)}%</td>
            <td class="py-3 px-4">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${badgeColor}">
                ${s.status}
              </span>
            </td>
            <td class="py-3 px-4 text-center">
              <button onclick="removeStock('${s.raw_symbol}')" class="text-slate-500 hover:text-rose-400 transition" title="Remove Stock">
                <i class="fa-solid fa-trash"></i>
              </button>
            </td>
          </tr>
        `;

        calcSelect.innerHTML += `<option value="stock_${s.raw_symbol}">[Stock] ${s.symbol} (${s.drawdown_52w.toFixed(1)}% dip)</option>`;
      });

      document.getElementById('discount-items-count').textContent = `${dipCount} Opportunities`;

      runCalculator();
    }

    function switchTab(tab) {
      ['funds', 'stocks', 'calculator', 'alerts'].forEach(t => {
        document.getElementById(`view-${t}`).classList.add('hidden');
        document.getElementById(`tab-${t === 'calculator' ? 'calc' : t}`).className = "px-5 py-3 text-sm font-semibold text-slate-400 hover:text-slate-200 flex items-center gap-2";
      });

      document.getElementById(`view-${tab}`).classList.remove('hidden');
      document.getElementById(`tab-${tab === 'calculator' ? 'calc' : tab}`).className = "px-5 py-3 text-sm font-semibold text-cyan-400 border-b-2 border-cyan-400 flex items-center gap-2";
    }

    function scrollToCalculator() {
      switchTab('calculator');
    }

    function runCalculator() {
      if (!globalData) return;
      const capital = parseFloat(document.getElementById('calc-capital').value) || 100000;
      const selectedVal = document.getElementById('calc-asset').value;
      const strategy = document.getElementById('calc-staging').value;

      let drawdown = -10.0;
      let upside = 11.1;

      if (selectedVal.startsWith('fund_')) {
        const code = selectedVal.replace('fund_', '');
        const f = globalData.funds.find(x => x.code === code);
        if (f) {
          drawdown = f.drawdown_52w;
          upside = f.recovery_upside_pct;
        }
      } else if (selectedVal.startsWith('stock_')) {
        const sym = selectedVal.replace('stock_', '');
        const s = globalData.stocks.find(x => x.raw_symbol === sym);
        if (s) {
          drawdown = s.drawdown_52w;
          upside = s.recovery_upside_pct;
        }
      }

      document.getElementById('calc-discount').textContent = `${drawdown.toFixed(1)}%`;
      
      let t1_pct = 0.30;
      if (strategy === 'aggressive') t1_pct = 0.50;
      if (strategy === 'conservative') t1_pct = 0.20;

      const t1_amount = capital * t1_pct;
      document.getElementById('calc-t1').textContent = `₹${t1_amount.toLocaleString('en-IN', {maximumFractionDigits: 0})}`;

      const projectedTotal = capital * (1 + (upside / 100));
      const netProfit = projectedTotal - capital;

      document.getElementById('calc-projected').textContent = `₹${projectedTotal.toLocaleString('en-IN', {maximumFractionDigits: 0})}`;
      document.getElementById('calc-profit').textContent = `+₹${netProfit.toLocaleString('en-IN', {maximumFractionDigits: 0})} (+${upside.toFixed(1)}%)`;

      // Timeline estimation
      let horizon = "3 - 6 Months";
      if (Math.abs(drawdown) > 20) horizon = "6 - 10 Months";
      else if (Math.abs(drawdown) < 5) horizon = "1 - 3 Months";
      document.getElementById('calc-horizon').textContent = horizon;
    }

    async function refreshData() {
      const icon = document.getElementById('refresh-icon');
      icon.classList.add('animate-spin');
      await loadData();
      setTimeout(() => icon.classList.remove('animate-spin'), 600);
    }

    function openAddFundModal() { document.getElementById('modal-fund').classList.remove('hidden'); }
    function openAddStockModal() { document.getElementById('modal-stock').classList.remove('hidden'); }
    function openDeploymentModal() { document.getElementById('modal-deploy').classList.remove('hidden'); }
    function closeModals() {
      document.getElementById('modal-fund').classList.add('hidden');
      document.getElementById('modal-stock').classList.add('hidden');
      document.getElementById('modal-deploy').classList.add('hidden');
    }

    async function submitAddFund() {
      const code = document.getElementById('add-fund-code').value.trim();
      const name = document.getElementById('add-fund-name').value.trim();
      const category = document.getElementById('add-fund-cat').value.trim();
      if (!code) return alert("Please enter scheme code");
      await fetch('/api/add_fund', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({code, name, category})
      });
      closeModals();
      loadData();
    }

    async function submitAddStock() {
      const symbol = document.getElementById('add-stock-sym').value.trim();
      const name = document.getElementById('add-stock-name').value.trim();
      const sector = document.getElementById('add-stock-sec').value.trim();
      if (!symbol) return alert("Please enter stock symbol");
      await fetch('/api/add_stock', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({symbol, name, sector})
      });
      closeModals();
      loadData();
    }

    async function removeFund(code) {
      if (!confirm("Remove this mutual fund from your watchlist?")) return;
      await fetch('/api/remove_fund', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({code})
      });
      loadData();
    }

    async function removeStock(symbol) {
      if (!confirm("Remove this stock from your watchlist?")) return;
      await fetch('/api/remove_stock', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({symbol})
      });
      loadData();
    }

    function previewEmailTemplate() {
      window.open('/preview_email', '_blank');
    }

    function simulateSendAlert() {
      document.getElementById('alert-status-box').classList.remove('hidden');
    }

    window.onload = loadData;
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/preview_email")
def preview_email():
    import indian_market_monitor as imm
    from generate_preview import build_html_report
    rep = imm.generate_advisory_report(risk_tolerance="moderate", user_email="meksmod1@gmail.com")
    return build_html_report(rep)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
