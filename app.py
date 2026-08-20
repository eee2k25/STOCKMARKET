"""app.py — multi-user Flask backend for MEK Stock Alert Pro.

Every account gets private, session-scoped storage (SQLite via user_db.py):

  * Google Sign-In via authlib — enabled by setting the GOOGLE_CLIENT_ID and
    GOOGLE_CLIENT_SECRET environment variables (see README for the full OAuth
    setup). Without them the email/password fallback keeps the app fully
    usable out of the box.
  * Per-user watchlist (funds + stocks), holdings (manual or broker CSV
    import), alert settings, and a personalised digest email.

Signed-out visitors see the shared market overview (the same single-profile
view Streamlit serves). Signed-in users see only their own data.
"""

import os
import threading
import datetime

from flask import Flask, jsonify, request, session, redirect, url_for

import user_db
from market_data import (
    load_config,
    collect_market_data,
    collect_holdings_valuation,
    search_instruments,
)
import nifty100_intraday_scanner as scanner

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = os.path.join(BASE_DIR, "interactive_portfolio_app.html")

app = Flask(__name__)
_secret_key = os.getenv("SECRET_KEY")
if not _secret_key:
    import secrets
    _secret_key = secrets.token_hex(32)
    app.logger.warning(
        "SECRET_KEY env var not set — using a random key. "
        "Sessions will not survive a restart; set SECRET_KEY in production."
    )
app.config["SECRET_KEY"] = _secret_key
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(days=30)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# ---------------------------------------------------------------------------
# Google OAuth (optional). Register a client at
# https://console.cloud.google.com/apis/credentials -> OAuth client ID
# ---------------------------------------------------------------------------
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_OAUTH = None
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    from authlib.integrations.flask_client import OAuth

    oauth = OAuth(app)
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    GOOGLE_OAUTH = oauth.google
    app.logger.info("Google Sign-In enabled.")
else:
    app.logger.info(
        "Google Sign-In disabled (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set). "
        "Email/password accounts remain available."
    )


# ---------------------------------------------------------------------------
# Caching: the shared (signed-out) payload is cached 5 min like before;
# personalised payloads get a short per-user cache (60 s) so watchlist and
# holdings edits show up immediately when the UI passes ?fresh=1.
# ---------------------------------------------------------------------------
GLOBAL_CACHE_TTL = 300
USER_CACHE_TTL = 60
_cache = {"data": None, "ts": 0.0}
_user_cache = {}
_cache_lock = threading.Lock()


def _cached(key, ttl, fresh, builder):
    now = datetime.datetime.now().timestamp()
    with _cache_lock:
        entry = _user_cache.get(key) if key != "global" else _cache
        data = entry.get("data") if entry else None
        if not fresh and data is not None and (now - entry.get("ts", 0)) < ttl:
            return data
    data = builder()
    with _cache_lock:
        if key == "global":
            _cache.update({"data": data, "ts": now})
        else:
            _user_cache[key] = {"data": data, "ts": now}
    return data


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return user_db.get_user(uid)


def _require_user():
    user = current_user()
    if user is None:
        return None
    return user


def _user_payload(user):
    return {
        "user": user,
        "google_configured": bool(GOOGLE_OAUTH),
    }


# ---------------------------------------------------------------------------
# Auth routes — email/password
# ---------------------------------------------------------------------------

@app.route("/api/me", methods=["GET"])
def api_me():
    return jsonify(_user_payload(current_user()))


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()
    if not email or "@" not in email or len(email) < 5:
        return jsonify({"success": False, "error": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters."}), 400
    if user_db.get_user_by_email(email):
        return jsonify({"success": False, "error": "An account with this email already exists — sign in instead."}), 409
    try:
        user = user_db.create_user(email=email, password=password, name=name)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    session["user_id"] = user["id"]
    session.permanent = True
    return jsonify({"success": True, **_user_payload(user)})


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = user_db.verify_password(email, password)
    if user is None:
        return jsonify({"success": False, "error": "Incorrect email or password."}), 401
    session["user_id"] = user["id"]
    session.permanent = True
    return jsonify({"success": True, **_user_payload(user)})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Auth routes — Google OAuth
# ---------------------------------------------------------------------------

@app.route("/login/google")
def google_login():
    if GOOGLE_OAUTH is None:
        return jsonify({
            "success": False,
            "error": "Google Sign-In is not configured. Set GOOGLE_CLIENT_ID and "
                     "GOOGLE_CLIENT_SECRET (see README) or use email/password.",
        }), 503
    return GOOGLE_OAUTH.authorize_redirect(url_for("google_callback", _external=True))


@app.route("/auth/google/callback")
def google_callback():
    if GOOGLE_OAUTH is None:
        return redirect("/")
    try:
        token = GOOGLE_OAUTH.authorize_access_token()
        userinfo = token.get("userinfo") or {}
        g_sub = userinfo.get("sub")
        g_email = (userinfo.get("email") or "").strip().lower()
        g_name = userinfo.get("name") or ""
        if not g_sub:
            return redirect("/?auth_error=google_missing_profile")
    except Exception as e:
        app.logger.exception("Google OAuth callback failed")
        return redirect("/?auth_error=google_failed")

    # 1) existing Google identity -> sign in
    user = user_db.get_user_by_google_sub(g_sub)
    # 2) same email via email/password -> link the Google identity
    if user is None and g_email:
        user = user_db.get_user_by_email(g_email)
        if user is not None:
            user_db.link_google_account(user["id"], g_sub)
    # 3) brand-new account
    if user is None:
        try:
            user = user_db.create_user(email=g_email or f"user_{g_sub[:8]}@google.local",
                                       name=g_name, google_sub=g_sub)
        except ValueError as e:
            app.logger.warning("Google account creation failed: %s", e)
            return redirect("/?auth_error=google_failed")

    session["user_id"] = user["id"]
    session.permanent = True
    return redirect("/")


# ---------------------------------------------------------------------------
# Market data — shared vs personalised
# ---------------------------------------------------------------------------

@app.route("/api/data", methods=["GET"])
def api_data():
    fresh = request.args.get("fresh") in ("1", "true")
    user = current_user()
    if user is None:
        return jsonify(_cached("global", GLOBAL_CACHE_TTL, fresh, _global_data))
    return jsonify(_cached(f"user:{user['id']}", USER_CACHE_TTL, fresh,
                            lambda: _personal_data(user)))


def _global_data():
    data = collect_market_data()
    data["user"] = None
    data["google_configured"] = bool(GOOGLE_OAUTH)
    return data


def _personal_data(user):
    cfg = user_db.watchlist_cfg(user["id"])
    data = collect_market_data(cfg=cfg)
    settings = user_db.settings_get(user["id"])
    holdings = user_db.holdings_list(user["id"])
    val = collect_holdings_valuation(holdings)
    # merge the user's alert settings into the config surface so the UI's
    # KPI row reflects *their* profile, not the global default
    data["config"] = {**cfg, **settings}
    data["user"] = user
    data["google_configured"] = bool(GOOGLE_OAUTH)
    data["settings"] = settings
    data["holdings"] = val["holdings"]
    data["portfolio"] = val["totals"]
    data["portfolio_as_of"] = val["as_of"]
    data["watchlist_count"] = {
        "funds": len(cfg.get("funds", {})),
        "stocks": len(cfg.get("stocks", {})),
    }
    return data


@app.route("/api/scan_nifty100", methods=["GET"])
def api_scan_nifty100():
    try:
        opps = scanner.scan_nifty_100(threshold_pct=-2.0)
        return jsonify({"success": True, "opportunities": opps, "count": len(opps)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Watchlist APIs (scoped to the signed-in user)
# ---------------------------------------------------------------------------

@app.route("/api/search", methods=["GET"])
def api_search():
    if _require_user() is None:
        return jsonify({"success": False, "error": "Sign in to add instruments."}), 401
    q = request.args.get("q", "")
    limit = min(int(request.args.get("limit", 12) or 12), 25)
    return jsonify({"success": True, **search_instruments(q, limit)})


@app.route("/api/watchlist", methods=["POST"])
def api_watchlist_add():
    user = _require_user()
    if user is None:
        return jsonify({"success": False, "error": "Sign in to save a watchlist."}), 401
    data = request.get_json(silent=True) or {}
    kind = data.get("kind") if data.get("kind") in ("funds", "stocks") else None
    symbol = (data.get("symbol") or "").strip()
    if kind is None or not symbol:
        return jsonify({"success": False, "error": "kind (funds/stocks) and symbol are required."}), 400
    if kind == "stocks" and not symbol.upper().endswith(".NS"):
        symbol = f"{symbol.upper()}.NS"
    try:
        item = user_db.watchlist_add(
            user["id"], kind, symbol,
            name=data.get("name", ""), category=data.get("category", ""),
            rating=data.get("rating", ""), sector=data.get("sector", ""),
        )
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    return jsonify({"success": True, "item": item})


@app.route("/api/watchlist/<kind>/<path:symbol>", methods=["DELETE"])
def api_watchlist_remove(kind, symbol):
    user = _require_user()
    if user is None:
        return jsonify({"success": False, "error": "Sign in to manage your watchlist."}), 401
    if kind not in ("funds", "stocks"):
        return jsonify({"success": False, "error": "Unknown kind."}), 400
    removed = user_db.watchlist_remove(user["id"], kind, symbol)
    return jsonify({"success": removed})


# ---------------------------------------------------------------------------
# Holdings APIs (manual + broker CSV import)
# ---------------------------------------------------------------------------

def _parse_holding_row(row, index):
    """Validate one holding row from the API/CSV import."""
    kind = (row.get("kind") or "stocks")
    if kind not in ("funds", "stocks"):
        raise ValueError(f"Row {index}: kind must be funds or stocks.")
    symbol = (row.get("symbol") or "").strip()
    if not symbol:
        raise ValueError(f"Row {index}: missing symbol.")
    if kind == "stocks" and not symbol.upper().endswith(".NS"):
        symbol = f"{symbol.upper()}.NS"
    try:
        qty = float(row.get("qty"))
        buy_price = float(row.get("buy_price"))
    except (TypeError, ValueError):
        raise ValueError(f"Row {index}: qty and buy_price must be numbers.")
    if qty <= 0 or buy_price <= 0:
        raise ValueError(f"Row {index}: qty and buy_price must be positive.")
    return {
        "kind": kind,
        "symbol": symbol,
        "name": (row.get("name") or symbol).strip(),
        "qty": qty,
        "buy_price": buy_price,
        "buy_date": (row.get("buy_date") or "").strip() or None,
        "notes": (row.get("notes") or "").strip(),
    }


@app.route("/api/holdings", methods=["GET"])
def api_holdings_get():
    user = _require_user()
    if user is None:
        return jsonify({"success": False, "error": "Sign in to view holdings."}), 401
    val = collect_holdings_valuation(user_db.holdings_list(user["id"]))
    return jsonify({"success": True, **val})


@app.route("/api/holdings", methods=["POST"])
def api_holdings_add():
    user = _require_user()
    if user is None:
        return jsonify({"success": False, "error": "Sign in to save holdings."}), 401
    data = request.get_json(silent=True) or {}
    try:
        row = _parse_holding_row(data, 1)
        item, inserted = user_db.holdings_add(user["id"], **row)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    return jsonify({"success": True, "item": item, "inserted": inserted})


@app.route("/api/holdings/import", methods=["POST"])
def api_holdings_import():
    user = _require_user()
    if user is None:
        return jsonify({"success": False, "error": "Sign in to import holdings."}), 401
    data = request.get_json(silent=True) or {}
    rows = data.get("rows") or []
    if not rows:
        return jsonify({"success": False, "error": "No rows to import."}), 400
    imported, errors = 0, []
    for i, row in enumerate(rows, start=1):
        try:
            parsed = _parse_holding_row(row, i)
            _, inserted = user_db.holdings_add(user["id"], **parsed)
            if inserted:
                imported += 1
        except ValueError as e:
            errors.append(str(e))
    return jsonify({"success": True, "imported": imported, "errors": errors})


@app.route("/api/holdings/<int:holding_id>", methods=["DELETE"])
def api_holdings_remove(holding_id):
    user = _require_user()
    if user is None:
        return jsonify({"success": False, "error": "Sign in to manage holdings."}), 401
    removed = user_db.holdings_remove(user["id"], holding_id)
    return jsonify({"success": removed})


# ---------------------------------------------------------------------------
# Settings + per-user alert email
# ---------------------------------------------------------------------------

@app.route("/api/settings", methods=["GET"])
def api_settings_get():
    user = _require_user()
    if user is None:
        return jsonify({"success": False, "error": "Sign in to view settings."}), 401
    return jsonify({"success": True, "settings": user_db.settings_get(user["id"])})


@app.route("/api/settings", methods=["POST"])
def api_settings_set():
    user = _require_user()
    if user is None:
        return jsonify({"success": False, "error": "Sign in to update settings."}), 401
    data = request.get_json(silent=True) or {}
    try:
        settings = user_db.settings_set(
            user["id"],
            risk_profile=data.get("risk_profile"),
            dip_threshold=data.get("dip_threshold"),
            alert_frequency=data.get("alert_frequency"),
        )
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    return jsonify({"success": True, "settings": settings})


@app.route("/api/send_test_alert", methods=["POST"])
def api_send_test_alert():
    user = current_user()
    try:
        import send_email
        if user is None:
            send_email.send_daily_email()
            cfg = load_config()
            return jsonify({"success": True,
                            "message": f"Email alert dispatched to {cfg.get('email', 'your inbox')}!"})
        sent, message = send_email.send_user_daily_email(user)
        if sent:
            return jsonify({"success": True, "message": message})
        return jsonify({"success": False, "error": message})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ---------------------------------------------------------------------------
# Front-end
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    try:
        with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        from flask import abort
        abort(500, description="interactive_portfolio_app.html is missing from the project directory.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
