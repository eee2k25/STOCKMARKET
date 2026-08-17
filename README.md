[README.md](https://github.com/user-attachments/files/31132304/README.md)
# 📈 Indian Equity Market & Mutual Fund Downturn Monitor

Personalized monitoring and dip-buying investment advisory engine calibrated for **Moderate Risk Profile**.

- **Recipient Email:** `meksmod1@gmail.com`
- **Tracked Mutual Funds:** 9 Schemes (from your Groww Watchlist)
- **Tracked Equities:** Top Nifty 50 Blue-Chip Leaders
- **Live AMFI NAV & NSE Data Feeds**
- **100% Free Lifetime Hosting & Automation**

---

## 🚀 Quick Usage

### 1. Run the Live Web Dashboard
```bash
python app.py
```
Open `http://localhost:5000` in your browser.

### 2. Run Manual Scan / Email Alert
```bash
python send_email.py
```

---

## 🌐 100% Free Permanent Hosting Options

### Option 1: GitHub Actions (Free Automated Daily 4:00 PM IST Email)
1. Push this folder to a GitHub Repository.
2. Go to **Settings > Secrets and variables > Actions**.
3. Add:
   - `SENDER_EMAIL`: Your Gmail address.
   - `SENDER_APP_PASSWORD`: A 16-character Google App Password (generated in Google Account > Security > 2-Step Verification > App Passwords).
4. GitHub will automatically run the scan every trading day at 4:00 PM IST and email your personalized analysis to `meksmod1@gmail.com`.

### Option 2: Free Web App on Render / Streamlit Cloud / PythonAnywhere
- Connect the GitHub repository to **Render.com** (Free Web Service) or **Streamlit Community Cloud**.
- Access your live URL on mobile anytime and tap **"Add to Home Screen"** to use it like a mobile app.
