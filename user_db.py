"""user_db.py — SQLite storage layer for the multi-user MEK Stock Alert Pro.

Every account gets fully private, session-scoped storage:

  * users      — email/password accounts plus Google Sign-In identities
                 (google_sub). Passwords are stored as salted werkzeug hashes.
  * watchlist  — the funds / stocks a user cares about (per-user market tabs).
  * holdings   — portfolio lots added manually or imported from a broker CSV
                 export (Zerodha / Groww / Upstox …).
  * settings   — per-user alert settings (risk profile, dip threshold,
                 alert frequency).

The schema self-initialises at import time, so the database file is created
lazily on first import and a deleted/missing users.db can never crash the
server at request time — it is simply recreated.
"""

import os
import sqlite3
import threading
import datetime

from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DATABASE_PATH lets hosts like Render place the SQLite file on a persistent
# disk (e.g. DATABASE_PATH=/var/data/users.db). Defaults to the repo directory.
DB_FILE = os.getenv("DATABASE_PATH") or os.path.join(BASE_DIR, "users.db")

# Google identities are stored in a *partial* unique index: NULL / empty
# google_sub (email-signup accounts) may repeat freely, while real Google
# subs stay unique.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    name          TEXT NOT NULL DEFAULT '',
    google_sub    TEXT,
    created_at    TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub
    ON users(google_sub) WHERE google_sub IS NOT NULL AND google_sub != '';

CREATE TABLE IF NOT EXISTS watchlist (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind     TEXT NOT NULL CHECK (kind IN ('funds', 'stocks')),
    symbol   TEXT NOT NULL,
    name     TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    rating   TEXT NOT NULL DEFAULT '',
    sector   TEXT NOT NULL DEFAULT '',
    added_at TEXT NOT NULL,
    UNIQUE (user_id, kind, symbol)
);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_id);

CREATE TABLE IF NOT EXISTS holdings (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind     TEXT NOT NULL CHECK (kind IN ('funds', 'stocks')),
    symbol   TEXT NOT NULL,
    name     TEXT NOT NULL DEFAULT '',
    qty      REAL NOT NULL,
    buy_price REAL NOT NULL,
    buy_date TEXT,
    notes    TEXT NOT NULL DEFAULT '',
    added_at TEXT NOT NULL,
    UNIQUE (user_id, kind, symbol, qty, buy_price)
);
CREATE INDEX IF NOT EXISTS idx_holdings_user ON holdings(user_id);

CREATE TABLE IF NOT EXISTS settings (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    risk_profile    TEXT NOT NULL DEFAULT 'moderate',
    dip_threshold   REAL NOT NULL DEFAULT 2.5,
    alert_frequency TEXT NOT NULL DEFAULT 'instant_and_eod',
    updated_at      TEXT NOT NULL
);
"""

_lock = threading.Lock()


def _init_db():
    """Create tables/indexes if they don't exist (safe to call repeatedly)."""
    with _lock:
        with sqlite3.connect(DB_FILE) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()


_init_db()  # self-initialise at import — see module docstring


def _connect():
    return sqlite3.connect(DB_FILE)


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _row_to_user(row):
    if row is None:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"] or row["email"].split("@")[0],
        "auth": "google" if row["google_sub"] else "email",
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def create_user(email, password=None, name="", google_sub=None):
    """Create an account. Raises ValueError on duplicate email."""
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        raise ValueError("A valid email address is required.")
    if google_sub is None and (not password or len(password) < 6):
        raise ValueError("Password must be at least 6 characters.")
    with _lock:
        with _connect() as conn:
            try:
                cur = conn.execute(
                    "INSERT INTO users (email, password_hash, name, google_sub, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (email,
                     generate_password_hash(password) if password else None,
                     (name or "").strip(),
                     google_sub or None,
                     _now()),
                )
                conn.commit()
                return get_user(cur.lastrowid)
            except sqlite3.IntegrityError:
                raise ValueError("An account with this email already exists.")


def get_user(user_id):
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _row_to_user(row)


def get_user_by_email(email):
    if not email:
        return None
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
        return _row_to_user(row)


def get_user_by_google_sub(google_sub):
    if not google_sub:
        return None
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE google_sub = ?", (google_sub,)
        ).fetchone()
        return _row_to_user(row)


def verify_password(email, password):
    """Return the user dict if the password matches, else None."""
    if not email or not password:
        return None
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    if row is None or not row["password_hash"]:
        return None
    if check_password_hash(row["password_hash"], password):
        return _row_to_user(row)
    return None


def link_google_account(user_id, google_sub):
    """Attach a Google identity to an existing email account."""
    if not google_sub:
        return False
    with _lock:
        with _connect() as conn:
            conn.execute("UPDATE users SET google_sub = ? WHERE id = ?", (google_sub, user_id))
            conn.commit()
    return True


def update_user_name(user_id, name):
    with _lock:
        with _connect() as conn:
            conn.execute("UPDATE users SET name = ? WHERE id = ?", (name or "", user_id))
            conn.commit()


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

def watchlist_add(user_id, kind, symbol, name="", category="", rating="", sector=""):
    """Add an instrument to a user's watchlist (idempotent). Returns the row."""
    kind = kind if kind in ("funds", "stocks") else "stocks"
    symbol = (symbol or "").strip()
    if not symbol:
        raise ValueError("A symbol / scheme code is required.")
    with _lock:
        with _connect() as conn:
            conn.row_factory = sqlite3.Row
            conn.execute(
                "INSERT OR IGNORE INTO watchlist "
                "(user_id, kind, symbol, name, category, rating, sector, added_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, kind, symbol, (name or "").strip(), (category or "").strip(),
                 (rating or "").strip(), (sector or "").strip(), _now()),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM watchlist WHERE user_id = ? AND kind = ? AND symbol = ?",
                (user_id, kind, symbol),
            ).fetchone()
    return dict(row)


def watchlist_remove(user_id, kind, symbol):
    with _lock:
        with _connect() as conn:
            cur = conn.execute(
                "DELETE FROM watchlist WHERE user_id = ? AND kind = ? AND symbol = ?",
                (user_id, kind, symbol),
            )
            conn.commit()
            return cur.rowcount > 0


def watchlist_list(user_id):
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM watchlist WHERE user_id = ? ORDER BY kind, added_at", (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def watchlist_cfg(user_id):
    """Build the market_data config shape for a user's watchlist.

    Returns {"funds": {code: {name, category, rating}}, "stocks": {sym: {name, sector}}}.
    """
    cfg = {"funds": {}, "stocks": {}}
    for r in watchlist_list(user_id):
        if r["kind"] == "funds":
            cfg["funds"][r["symbol"]] = {
                "name": r["name"] or r["symbol"],
                "category": r["category"] or "Mutual Fund",
                "rating": r["rating"] or "4★",
            }
        else:
            cfg["stocks"][r["symbol"]] = {
                "name": r["name"] or r["symbol"],
                "sector": r["sector"] or "NSE",
            }
    return cfg


# ---------------------------------------------------------------------------
# Holdings
# ---------------------------------------------------------------------------

def holdings_add(user_id, kind, symbol, name="", qty=None, buy_price=None, buy_date=None, notes=""):
    """Add a holding lot. Returns (row, inserted). Duplicate lots (same
    kind/symbol/qty/buy_price) are ignored."""
    kind = kind if kind in ("funds", "stocks") else "stocks"
    symbol = (symbol or "").strip()
    if not symbol:
        raise ValueError("A symbol / scheme code is required.")
    try:
        qty = float(qty)
        buy_price = float(buy_price)
    except (TypeError, ValueError):
        raise ValueError("Quantity and buy price must be numbers.")
    if qty <= 0 or buy_price <= 0:
        raise ValueError("Quantity and buy price must be greater than zero.")
    with _lock:
        with _connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "INSERT OR IGNORE INTO holdings "
                "(user_id, kind, symbol, name, qty, buy_price, buy_date, notes, added_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, kind, symbol, (name or "").strip(), qty, buy_price,
                 (buy_date or "").strip() or None, (notes or "").strip(), _now()),
            )
            conn.commit()
            inserted = cur.rowcount > 0
            row = conn.execute(
                "SELECT * FROM holdings WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            if row is None:  # duplicate — fetch the existing lot
                row = conn.execute(
                    "SELECT * FROM holdings WHERE user_id = ? AND kind = ? AND symbol = ? "
                    "AND qty = ? AND buy_price = ?",
                    (user_id, kind, symbol, qty, buy_price),
                ).fetchone()
    return dict(row), inserted


def holdings_list(user_id):
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM holdings WHERE user_id = ? ORDER BY added_at DESC", (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def holdings_remove(user_id, holding_id):
    with _lock:
        with _connect() as conn:
            cur = conn.execute(
                "DELETE FROM holdings WHERE id = ? AND user_id = ?", (holding_id, user_id)
            )
            conn.commit()
            return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

DEFAULT_SETTINGS = {
    "risk_profile": "moderate",
    "dip_threshold": 2.5,
    "alert_frequency": "instant_and_eod",
}

_VALID_RISK = {"conservative", "moderate", "aggressive"}
_VALID_FREQ = {"instant_and_eod", "eod_only"}


def settings_get(user_id):
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM settings WHERE user_id = ?", (user_id,)
        ).fetchone()
    out = dict(DEFAULT_SETTINGS)
    if row:
        out.update({k: row[k] for k in DEFAULT_SETTINGS})
    return out


def settings_set(user_id, risk_profile=None, dip_threshold=None, alert_frequency=None):
    cur_settings = settings_get(user_id)
    risk = (risk_profile or cur_settings["risk_profile"]).strip().lower()
    freq = (alert_frequency or cur_settings["alert_frequency"]).strip().lower()
    if risk not in _VALID_RISK:
        raise ValueError("risk_profile must be one of conservative, moderate, aggressive.")
    if freq not in _VALID_FREQ:
        raise ValueError("alert_frequency must be one of instant_and_eod, eod_only.")
    try:
        threshold = float(dip_threshold) if dip_threshold is not None else float(cur_settings["dip_threshold"])
    except (TypeError, ValueError):
        raise ValueError("dip_threshold must be a number.")
    if not (0 < threshold <= 15):
        raise ValueError("dip_threshold must be between 0 and 15 percent.")
    with _lock:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO settings (user_id, risk_profile, dip_threshold, alert_frequency, updated_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET "
                "risk_profile = excluded.risk_profile, "
                "dip_threshold = excluded.dip_threshold, "
                "alert_frequency = excluded.alert_frequency, "
                "updated_at = excluded.updated_at",
                (user_id, risk, threshold, freq, _now()),
            )
            conn.commit()
    return settings_get(user_id)
