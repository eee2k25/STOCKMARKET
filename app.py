import datetime
import threading
from flask import Flask, jsonify, request, abort

from market_data import load_config, collect_market_data
import nifty100_intraday_scanner as scanner

app = Flask(__name__)

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = os.path.join(BASE_DIR, "interactive_portfolio_app.html")

# ---------------------------------------------------------------------------
# Lightweight server-side cache so repeated page loads don't re-hit the feeds
# ---------------------------------------------------------------------------
CACHE_TTL_SECONDS = 300
_cache = {"data": None, "ts": 0.0}
_cache_lock = threading.Lock()


@app.route("/api/data", methods=["GET"])
def get_market_data():
    fresh = request.args.get("fresh") in ("1", "true")
    now = datetime.datetime.now().timestamp()
    with _cache_lock:
        if not fresh and _cache["data"] and (now - _cache["ts"]) < CACHE_TTL_SECONDS:
            return jsonify(_cache["data"])
    data = collect_market_data()
    with _cache_lock:
        _cache["data"] = data
        _cache["ts"] = now
    return jsonify(data)


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
        cfg = load_config()
        return jsonify({"success": True, "message": f"Email alert dispatched to {cfg.get('email', 'your inbox')}!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/")
def index():
    try:
        with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        abort(500, description="interactive_portfolio_app.html is missing from the project directory.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
