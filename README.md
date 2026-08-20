# 📈 Indian Equity Market & Mutual Fund Downturn Monitor

Personalized monitoring and dip-buying investment advisory engine calibrated for your risk profile — now with **multi-user accounts**.

- **Multi-user Flask app** (`app.py`): Google Sign-In (optional) + email/password fallback, private per-user watchlists, holdings & alert settings in SQLite
- **Live Portfolio tab**: add holdings manually or paste a **broker CSV export** (Zerodha / Groww / Upstox) — live value, day change and P&L per lot
- **Live AMFI NAV & NSE Data Feeds** (demo fallback keeps the UI usable offline)
- **Per-user email digests** with a personal portfolio section
- **100% Free Lifetime Hosting & Automation**

---

## 🚀 Quick Usage

### 1. Run the Live Web Dashboard (recommended)
```bash
pip install -r requirements.txt
python app.py
```
Open `http://localhost:5000` — the full interactive cream · gold · red dashboard (sign-in, watchlist, portfolio, scanner, test alerts).

### 2. Run the Streamlit App (shared single-profile view)
```bash
streamlit run streamlit_app.py
```
> **Note:** Streamlit Cloud can't run real OAuth logins, so the Streamlit app stays the *shared* single-profile view. All multi-user features live in the Flask app (deployable free on Render).

### 3. Run Manual Scan / Email Alert
```bash
python send_email.py
```

### 4. Run the test suite
```bash
python tests/test_multi_user.py    # 54 checks: registration, isolation, CSV, settings…
```

---

## 👥 Multi-user accounts

Every account gets its own private watchlist (funds + stocks), portfolio holdings, alert settings and digest email — fully isolated per user (verified by the test suite with two accounts).

**Signed-out visitors** see the shared market overview (same as the Streamlit view). **Signed-in users** see only their own data.

| | Signed-out / Streamlit | Signed-in account |
|---|---|---|
| Watchlist | Default 9 funds + 10 stocks | Yours — starts empty, add any NSE stock or mutual fund |
| My Portfolio tab | Hidden | Yours — manual + CSV import, live P&L |
| Alert settings | Global defaults | Yours (risk profile, dip threshold, frequency) |
| Send Test Alert | Global digest | *Your* digest to *your* email with *your* portfolio |

### Google Sign-In setup (optional — email/password works out of the box)
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → **Create credentials → OAuth client ID**.
2. Application type: **Web application**. Add the redirect URI:
   `https://YOUR-APP-DOMAIN/auth/google/callback` (for local dev: `http://localhost:5000/auth/google/callback`).
3. Set these environment variables when running/deploying the app:
   ```
   GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-xxxx
   SECRET_KEY=some-long-random-string      # signs session cookies
   ```
4. Restart. The dashboard's **Sign in** modal now shows *Continue with Google*.

Without those env vars the app still works fully: new users sign up with email + password (passwords are salted-hashed, sessions are signed cookies).

### Email alerts (per user)
Set `SENDER_EMAIL` and `SENDER_APP_PASSWORD` (a 16-character Gmail App Password, generated at Google Account → Security → 2-Step Verification → App Passwords). Then each user's **Send Test Alert** dispatches *their* digest to *their* inbox — watchlist, risk-profile tranche plan and portfolio section included.

---

## 💼 Portfolio & CSV import

The **My Portfolio** tab lets you:
- **Add holdings manually** — NSE symbol (e.g. `RELIANCE` or `TCS.NS`) or AMFI scheme code, quantity, buy price, date.
- **Import a broker CSV export** — paste the holdings CSV from your Zerodha / Groww / Upstox console (any export with symbol, quantity and average-price columns works). Duplicate lots are skipped; unrecognised rows are reported.

Live NSE quotes / AMFI NAVs value each lot, with day change and P&L (₹ and %) plus portfolio totals.

---

## 🌐 100% Free Permanent Hosting Options

### Option 1: GitHub Actions (Free Automated Daily 4:00 PM IST Email)
1. Push this folder to a GitHub Repository.
2. Go to **Settings > Secrets and variables > Actions** and add `SENDER_EMAIL` / `SENDER_APP_PASSWORD`.
3. GitHub runs the scan every trading day at 4:00 PM IST and emails the digest (this uses the *global* default recipient config).

### Option 2: Free Web App on Render (multi-user)
1. Connect the repo to **Render.com → New Web Service**.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app`
4. Add the env vars above (`SECRET_KEY`, and optionally `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `SENDER_EMAIL` / `SENDER_APP_PASSWORD`).

### Option 3: Streamlit Community Cloud
Shared single-profile dashboard — `streamlit run streamlit_app.py` with `requirements.txt`.

---

## 🧱 Project layout

| File | Role |
|---|---|
| `app.py` | Multi-user Flask backend: OAuth + email/password auth, per-user APIs |
| `user_db.py` | SQLite storage (users, watchlists, holdings, settings) |
| `market_data.py` | Live feeds, holdings valuation, instrument search |
| `interactive_portfolio_app.html` | The full dashboard UI (auth, modals, portfolio) |
| `send_email.py` / `generate_preview.py` | Per-user digest email |
| `streamlit_app.py` | Shared single-profile Streamlit view |
| `tests/test_multi_user.py` | End-to-end multi-user test suite |

---

Mutual fund investments are subject to market risks. Personal advisory tool — not investment advice.
