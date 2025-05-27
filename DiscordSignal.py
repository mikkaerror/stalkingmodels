import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials

# ───────── Setup ─────────
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcreds2.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Earnings Tracker").sheet1

# ───────── Discord Webhook ─────────
webhook_url = "https://discord.com/api/webhooks/1376409108567293963/L5ue3HrF6exHuClXdVNpvh7LiBTRUVYUVO552uBJEdUFPiOhSskbJwzgpT6RJ2ow23Lu"

# ───────── Fetch Sheet Data ─────────
data = sheet.get_all_records()

# ───────── Process Each Row ─────────
for row in data:
    try:
        ticker = row.get("Ticker", "").strip()
        signal = row.get("Signal Trigger", "")
        if not ticker or not signal or "✅" not in signal:
            continue

        try:
            days_until = int(row.get("days until") or 999)
        except (ValueError, TypeError):
            days_until = 999

        if days_until > 30:
            continue

        # Pull fields with fallbacks
        setup = row.get("Setup Rec", "N/A")
        earnings = row.get("Next Earnings", "N/A")
        confidence = row.get("Confidence (3 MAX)", "N/A")
        estimate = row.get("P/L Estimate (units of ATR%)", "N/A")
        dollar_pl = row.get("Dollar P/L", "N/A")
        urgency = row.get("Urgency", "N/A")
        iv_delta = row.get("IV Rank Change (5-day delta)", "N/A")
        z_score = row.get("ATR% Z-Score", "N/A")
        atr = row.get("20 Day ATR", "N/A")

        # ───────── Clean Discord Message ─────────
        message = f"""
**{ticker} — {setup}**

🗓️ Earnings in {days_until} days ({earnings})
✅ Signal Triggered

💵 {estimate} ATR  |  ${dollar_pl}
📊 IV Δ (5d): {iv_delta}  |  Z: {z_score}  |  ATR: ${atr}
🧠 Confidence: {confidence}  |  ⚡ Urgency: {urgency}
""".strip()

        # ───────── Send to Discord ─────────
        payload = {"content": message}
        response = requests.post(webhook_url, json=payload)

        if response.status_code == 204:
            print(f"{ticker} ✅ Alert sent")
        else:
            print(f"{ticker} ❌ Failed — Status: {response.status_code}, Response: {response.text}")

    except Exception as e:
        print(f"{row.get('Ticker', 'UNKNOWN')} error: {e}")