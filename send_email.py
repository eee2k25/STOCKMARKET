#!/usr/bin/env python3
"""
Automated Daily Email Dispatcher for Indian Equity Markets & Mutual Funds
Sends HTML report to meksmod1@gmail.com using Gmail SMTP (Free)
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import indian_market_monitor as imm
from generate_preview import build_html_report

def send_daily_email():
    sender_email = os.environ.get("SENDER_EMAIL", "your_gmail@gmail.com")
    sender_password = os.environ.get("SENDER_APP_PASSWORD", "your_16_char_app_password")
    recipient_email = os.environ.get("RECIPIENT_EMAIL", "meksmod1@gmail.com")

    # Generate the live report
    rep = imm.generate_advisory_report(risk_tolerance="moderate", user_email=recipient_email)
    html_content = build_html_report(rep)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📈 Indian Market Alert: Daily Downturn & Dip Opportunities ({rep['timestamp']})"
    msg["From"] = f"Market Advisory Engine <{sender_email}>"
    msg["To"] = recipient_email

    msg.attach(MIMEText(html_content, "html"))

    try:
        # Standard Gmail SMTP connection
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        print(f"✅ Alert successfully emailed to {recipient_email}")
    except Exception as e:
        print(f"⚠️ SMTP Send skipped or configured for simulation: {e}")
        print("Note: To send actual emails, provide your free Gmail App Password in GitHub Secrets or environment variables.")

if __name__ == "__main__":
    send_daily_email()
