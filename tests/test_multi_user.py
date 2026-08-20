#!/usr/bin/env python3
"""End-to-end multi-user test suite for MEK Stock Alert Pro.

Covers the full account lifecycle: registration (including the Google-sub
collision scenario), login/logout, per-user watchlist & holdings isolation,
CSV import, per-user settings, personalised /api/data payloads, the
signed-out shared view, auth guards, and the demo-fill guard for empty
watchlists.

Network access is stubbed so the suite is deterministic and runs offline
(CI-friendly). Run with either:

    python tests/test_multi_user.py          # plain runner
    pytest tests/test_multi_user.py          # pytest discovery
"""
import os
import sys
import shutil
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import user_db
import market_data
import app as appmod

PASSED = []
FAILED = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    (PASSED if cond else FAILED).append(name)
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    return cond


# ---------------------------------------------------------------------------
# Fixtures: isolated temp DB + stubbed feeds
# ---------------------------------------------------------------------------

def _fresh_db():
    fd, path = tempfile.mkstemp(prefix="mek_users_", suffix=".db")
    os.close(fd)
    os.remove(path)  # give sqlite a clean, empty path in an existing dir
    user_db.DB_FILE = path
    user_db._init_db()
    return path


def _stub_network():
    """Deterministic market data / valuation stubs (no sockets, no disk)."""
    def fake_collect(cfg=None):
        cfg = cfg if cfg is not None else market_data.load_config()
        funds = cfg.get("funds") or {}
        stocks = cfg.get("stocks") or {}
        # no live feeds, no demo injection -> empty lists for empty cfg
        demo = bool(funds or stocks)  # configured-but-unreachable -> demo
        return {
            "timestamp": "01 Jan 2026, 09:30 AM IST",
            "config": cfg,
            "nifty": {"symbol": "NIFTY 50", "price": 24000.0, "change": -100.0,
                      "pct_change": -0.41, "high_52w": 26000.0,
                      "spark": [24000.0, 24050.0], "spark_dates": ["01 Jan 26", "02 Jan 26"]},
            "funds": [{"code": c, "name": m["name"], "category": m.get("category", ""),
                       "rating": m.get("rating", "4★"), "nav": 100.0, "date": "01 Jan 2026",
                       "change": 0.5, "pct_change": 0.5, "high_52w": 110.0,
                       "drawdown_52w": -9.1, "recovery_upside_pct": 10.0,
                       "status": "Value Pullback", "badge": "warning",
                       "spark": [100.0, 100.5], "spark_dates": ["01 Jan 26", "02 Jan 26"]}
                      for c, m in funds.items()],
            "stocks": [{"symbol": s.replace(".NS", ""), "raw_symbol": s, "name": m["name"],
                        "sector": m.get("sector", ""), "price": 500.0, "change": 2.0,
                        "pct_change": 0.4, "high_52w": 600.0, "drawdown_52w": -16.7,
                        "recovery_upside_pct": 20.0, "status": "Correction Zone",
                        "badge": "warning", "spark": [500.0, 502.0],
                        "spark_dates": ["01 Jan 26", "02 Jan 26"]}
                       for s, m in stocks.items()],
            "demo": demo,
        }

    def fake_valuation(holdings):
        valued = []
        for h in holdings:
            mult = 1.10 if h["kind"] == "stocks" else 1.05
            price = round(float(h["buy_price"]) * mult, 2)
            qty = float(h["qty"])
            current_value = round(price * qty, 2)
            cost = round(float(h["buy_price"]) * qty, 2)
            pnl = round(current_value - cost, 2)
            valued.append({
                "id": h["id"], "kind": h["kind"], "symbol": h["symbol"],
                "name": h["name"] or h["symbol"], "qty": qty,
                "buy_price": round(float(h["buy_price"]), 2),
                "buy_date": h.get("buy_date"), "current_price": price,
                "current_value": current_value, "day_change": 0.0, "day_pct": 0.0,
                "pnl": pnl, "pnl_pct": round((pnl / cost) * 100, 2) if cost else 0.0,
                "live": True,
            })
        invested = round(sum(v["buy_price"] * v["qty"] for v in valued), 2)
        current = round(sum(v["current_value"] for v in valued), 2)
        pnl = round(current - invested, 2)
        return {
            "holdings": valued,
            "totals": {"invested": invested, "current_value": current,
                       "day_change": 0.0, "day_pct": 0.0, "pnl": pnl,
                       "pnl_pct": round((pnl / invested) * 100, 2) if invested else 0.0,
                       "live": True},
            "as_of": "01 Jan 2026, 09:30 AM IST",
        }

    appmod.collect_market_data = fake_collect
    appmod.collect_holdings_valuation = fake_valuation


def _client():
    appmod.app.config["TESTING"] = True
    return appmod.app.test_client()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_register_and_login():
    c = _client()
    r = c.post("/api/register", json={"name": "Alice", "email": "alice@t.dev", "password": "secret1"})
    check("register alice 200", r.status_code == 200)
    u = r.get_json()["user"]
    check("register returns user", u["email"] == "alice@t.dev" and u["auth"] == "email")
    check("register creates session", c.get("/api/me").get_json()["user"]["email"] == "alice@t.dev")

    c.post("/api/logout")
    r = c.post("/api/login", json={"email": "alice@t.dev", "password": "wrong"})
    check("wrong password 401", r.status_code == 401)
    r = c.post("/api/login", json={"email": "alice@t.dev", "password": "secret1"})
    check("correct password 200", r.status_code == 200 and r.get_json()["user"]["email"] == "alice@t.dev")

    r = c.post("/api/register", json={"email": "alice@t.dev", "password": "secret1"})
    check("duplicate email 409", r.status_code == 409)
    r = c.post("/api/register", json={"email": "bob@t.dev", "password": "short"})
    check("short password 400", r.status_code == 400)


def test_two_email_users_do_not_collide():
    """The google_sub partial-unique-index scenario: email signups must not
    collide with each other (google_sub is NULL for them)."""
    c = _client()
    a = c.post("/api/register", json={"name": "A", "email": "a@t.dev", "password": "secret1"})
    b = c.post("/api/register", json={"name": "B", "email": "b@t.dev", "password": "secret1"})
    check("user A created", a.status_code == 200)
    check("user B created (no google_sub collision)", b.status_code == 200)
    check("different ids", a.get_json()["user"]["id"] != b.get_json()["user"]["id"])


def test_password_is_hashed():
    _fresh_db()
    user_db.create_user(email="a@t.dev", password="secret1", name="A")
    import sqlite3
    with sqlite3.connect(user_db.DB_FILE) as conn:
        cur = conn.execute("SELECT password_hash FROM users WHERE email = 'a@t.dev'")
        h = cur.fetchone()[0]
    check("password stored hashed", h and "secret1" not in h and (h.startswith("scrypt") or h.startswith("pbkdf2")), str(h)[:30])


def test_signed_out_shared_view():
    c = _client()
    d = c.get("/api/data").get_json()
    check("signed-out global view", d["user"] is None and len(d["funds"]) == 9 and len(d["stocks"]) == 10)
    check("google_configured flag present", "google_configured" in d)


def test_auth_guards():
    c = _client()
    check("watchlist add requires auth", c.post("/api/watchlist", json={"kind": "stocks", "symbol": "TCS.NS"}).status_code == 401)
    check("holdings add requires auth", c.post("/api/holdings", json={"kind": "stocks", "symbol": "TCS.NS", "qty": 1, "buy_price": 100}).status_code == 401)
    check("settings get requires auth", c.get("/api/settings").status_code == 401)
    check("search requires auth", c.get("/api/search?q=reli").status_code == 401)


def test_watchlist_isolation():
    c = _client()
    c.post("/api/register", json={"name": "A", "email": "a@t.dev", "password": "secret1"})
    c.post("/api/watchlist", json={"kind": "stocks", "symbol": "RELIANCE.NS"})
    c.post("/api/watchlist", json={"kind": "funds", "symbol": "119783", "name": "SBI Healthcare"})
    d = c.get("/api/data?fresh=1").get_json()
    stocks_a = [s["raw_symbol"] for s in d["stocks"]]
    funds_a = [f["code"] for f in d["funds"]]
    check("A sees own stock", stocks_a == ["RELIANCE.NS"])
    check("A sees own fund", funds_a == ["119783"])
    check("A settings present", d["settings"]["risk_profile"] == "moderate")

    c.post("/api/logout")
    c.post("/api/register", json={"name": "B", "email": "b@t.dev", "password": "secret1"})
    c.post("/api/watchlist", json={"kind": "stocks", "symbol": "TCS.NS"})
    d = c.get("/api/data?fresh=1").get_json()
    stocks_b = [s["raw_symbol"] for s in d["stocks"]]
    check("B does not see A's stock", stocks_b == ["TCS.NS"] and "RELIANCE.NS" not in stocks_b)
    check("B does not see A's fund", len(d["funds"]) == 0)
    check("B user id differs", d["user"]["id"] != None and d["user"]["email"] == "b@t.dev")

    # duplicate add is idempotent
    c.post("/api/watchlist", json={"kind": "stocks", "symbol": "tcs"})
    d = c.get("/api/data?fresh=1").get_json()
    check("watchlist dedupes", len(d["stocks"]) == 1)

    # remove
    r = c.delete("/api/watchlist/stocks/TCS.NS")
    check("watchlist remove", r.get_json()["success"] is True)
    d = c.get("/api/data?fresh=1").get_json()
    check("watchlist empty after remove", len(d["stocks"]) == 0)


def test_holdings_isolation_and_valuation():
    c = _client()
    c.post("/api/register", json={"name": "A", "email": "a@t.dev", "password": "secret1"})
    r = c.post("/api/holdings", json={"kind": "stocks", "symbol": "TCS", "name": "TCS Ltd", "qty": 10, "buy_price": 3500})
    check("holding added", r.status_code == 200)
    d = c.get("/api/data?fresh=1").get_json()
    t = d["portfolio"]
    check("portfolio value = 10*3500*1.1", t["current_value"] == 38500.0, str(t))
    check("portfolio invested", t["invested"] == 35000.0)
    check("portfolio pnl", t["pnl"] == 3500.0)
    check("holding in payload", len(d["holdings"]) == 1 and d["holdings"][0]["symbol"] == "TCS.NS")

    # funds holding at 5% uplift
    c.post("/api/holdings", json={"kind": "funds", "symbol": "119783", "name": "SBI Health", "qty": 100, "buy_price": 90})
    d = c.get("/api/data?fresh=1").get_json()
    check("two lots", len(d["holdings"]) == 2)
    check("fund lot valued x1.05", any(h["symbol"] == "119783" and h["current_price"] == 94.5 for h in d["holdings"]))

    # isolation: B sees nothing
    c.post("/api/logout")
    c.post("/api/register", json={"name": "B", "email": "b@t.dev", "password": "secret1"})
    d = c.get("/api/data?fresh=1").get_json()
    check("B portfolio empty", d["portfolio"]["invested"] == 0 and len(d["holdings"]) == 0)

    # delete A's lot as B must fail (scoped)
    r = c.delete(f"/api/holdings/{d['holdings'][0]['id']}" if d["holdings"] else "/api/holdings/999999")
    check("delete scoped to owner", r.status_code == 200 and r.get_json()["success"] is False)


def test_csv_import():
    c = _client()
    c.post("/api/register", json={"name": "A", "email": "a@t.dev", "password": "secret1"})
    rows = [
        {"kind": "stocks", "symbol": "INFY.NS", "qty": 5, "buy_price": 1400, "buy_date": "2026-01-10"},
        {"kind": "stocks", "symbol": "RELIANCE", "qty": 2, "buy_price": 2400},
        {"kind": "stocks", "symbol": "BAD", "qty": -1, "buy_price": 100},
        {"kind": "funds", "symbol": "119783", "name": "SBI Health", "qty": 50, "buy_price": 90},
    ]
    r = c.post("/api/holdings/import", json={"rows": rows})
    j = r.get_json()
    check("csv import counts", j["imported"] == 3 and len(j["errors"]) == 1, str(j))
    # duplicate lot ignored
    r = c.post("/api/holdings/import", json={"rows": [{"kind": "stocks", "symbol": "INFY.NS", "qty": 5, "buy_price": 1400}]})
    check("duplicate lot skipped", r.get_json()["imported"] == 0)
    d = c.get("/api/data?fresh=1").get_json()
    check("three unique lots after import", len(d["holdings"]) == 3, str([h["symbol"] for h in d["holdings"]]))
    check("symbol normalized to .NS", any(h["symbol"] == "RELIANCE.NS" for h in d["holdings"]))


def test_settings_per_user():
    c = _client()
    c.post("/api/register", json={"name": "A", "email": "a@t.dev", "password": "secret1"})
    r = c.post("/api/settings", json={"risk_profile": "aggressive", "dip_threshold": 3.0, "alert_frequency": "eod_only"})
    check("settings saved", r.status_code == 200 and r.get_json()["settings"]["risk_profile"] == "aggressive")
    d = c.get("/api/data?fresh=1").get_json()
    check("settings reflected in /api/data", d["settings"]["dip_threshold"] == 3.0 and d["config"]["risk_profile"] == "aggressive")

    c.post("/api/logout")
    c.post("/api/register", json={"name": "B", "email": "b@t.dev", "password": "secret1"})
    d = c.get("/api/data?fresh=1").get_json()
    check("B keeps defaults", d["settings"] == {"risk_profile": "moderate", "dip_threshold": 2.5, "alert_frequency": "instant_and_eod"})

    r = c.post("/api/settings", json={"risk_profile": "suicidal"})
    check("invalid risk profile rejected", r.status_code == 400)


def test_personalized_data_does_not_demo_fill():
    """A signed-in user with an empty watchlist gets empty funds/stocks and
    no demo data injected (the original bug)."""
    c = _client()
    c.post("/api/register", json={"name": "C", "email": "c@t.dev", "password": "secret1"})
    d = c.get("/api/data?fresh=1").get_json()
    check("empty watchlist -> empty lists", d["funds"] == [] and d["stocks"] == [])
    check("empty watchlist -> no demo flag", d["demo"] is False)


def test_google_unconfigured_503():
    c = _client()
    r = c.get("/login/google")
    check("google route 503 when unconfigured", r.status_code == 503 and r.get_json()["success"] is False)


def test_send_test_alert_signed_in_without_smtp():
    c = _client()
    c.post("/api/register", json={"name": "A", "email": "a@t.dev", "password": "secret1"})
    os.environ["SENDER_APP_PASSWORD"] = ""
    r = c.post("/api/send_test_alert")
    j = r.get_json()
    check("per-user alert reports SMTP unconfigured", j.get("success") is False and "SMTP" in (j.get("error") or ""), str(j))


def test_market_data_empty_cfg_guard():
    """Unit-level: collect_market_data(cfg=empty) never demo-fills."""
    orig = (market_data._nifty_payload, market_data._fund_payload, market_data._stock_payload)
    market_data._nifty_payload = lambda: None
    market_data._fund_payload = lambda c, m: None
    market_data._stock_payload = lambda s, m: None
    try:
        d = market_data.collect_market_data(cfg={"funds": {}, "stocks": {}})
        check("empty cfg -> no demo, empty lists", d["demo"] is False and d["funds"] == [] and d["stocks"] == [])
        d = market_data.collect_market_data(cfg={"funds": {"119783": {"name": "X", "category": "Test"}}, "stocks": {}})
        check("configured-but-down -> demo flag", d["demo"] is True and len(d["funds"]) == 1)
    finally:
        market_data._nifty_payload, market_data._fund_payload, market_data._stock_payload = orig


def test_search_offline_catalog():
    s = market_data.search_instruments("RELI")
    check("stock search finds RELIANCE.NS", any(x["symbol"] == "RELIANCE.NS" for x in s["stocks"]))
    f = market_data.search_instruments("sbi healthcare")
    check("fund search finds SBI Healthcare", any(x["symbol"] == "119783" for x in f["funds"]))
    e = market_data.search_instruments("")
    check("empty query -> empty", e == {"stocks": [], "funds": []})


def test_digest_email_builder_has_holdings_section():
    import generate_preview as gp
    rep = {
        "timestamp": "01 Jan 2026",
        "risk_profile": "moderate",
        "recipient_email": "a@t.dev",
        "index": {"price": 24000.0, "pct_change": -0.4, "high_52w": 26000.0},
        "stocks": [], "funds": [],
        "holdings": [{"kind": "stocks", "symbol": "TCS.NS", "name": "TCS Ltd", "qty": 10,
                      "buy_price": 3500.0, "current_price": 3850.0, "current_value": 38500.0,
                      "pnl": 3500.0, "pnl_pct": 10.0, "buy_date": "2026-01-10"}],
        "portfolio_totals": {"invested": 35000.0, "current_value": 38500.0, "day_change": 0.0,
                             "day_pct": 0.0, "pnl": 3500.0, "pnl_pct": 10.0},
    }
    html = gp.build_html_report(rep)
    check("digest contains portfolio section", "Your portfolio (1 lot)" in html and "TCS.NS" in html)
    html2 = gp.build_html_report({**rep, "holdings": []})
    check("digest without holdings omits section", "Your portfolio" not in html2)


def main():
    print("\n=== MEK multi-user test suite ===")
    _fresh_db()
    _stub_network()

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        _fresh_db()
        try:
            t()
        except Exception as e:
            import traceback
            check(t.__name__, False, f"{type(e).__name__}: {e}")
            traceback.print_exc()
    print(f"\n=== {len(PASSED)} passed, {len(FAILED)} failed ===")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
