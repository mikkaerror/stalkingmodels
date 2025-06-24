import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials

# ───────── Google Sheets Setup ─────────
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

        # ───── Extract Fields ─────
        setup = row.get("Setup Rec", "N/A")
        earnings = row.get("Next Earnings", "N/A")
        confidence = row.get("Confidence (3 MAX)", "N/A")
        urgency = row.get("Urgency", "N/A")

        # Safe numeric values
        estimate = float(row.get("P/L Estimate (units of ATR%)") or 0)
        dollar_pl = float(str(row.get("Dollar P/L", "0")).replace("$", "").replace(",", "") or 0)
        iv_delta = float(row.get("IV Rank Change (5-day delta)") or 0)
        z_score = float(row.get("ATR% Z-Score") or 0)
        atr_val = float(str(row.get("20 Day ATR", "0")).replace("$", "").replace(",", "") or 0)

        # ───── Format Values ─────
        est_str = f"{estimate:.2f}"
        pl_str = f"${dollar_pl:,.2f}"
        iv_str = f"{iv_delta:+.2f}"
        z_str = f"{z_score:+.2f}"
        atr_str = f"${atr_val:.2f}"

        # ───── Discord Message ─────
        message = f"""📈 `{ticker}` — {setup} | Earnings: {earnings} (in {days_until}d)
ATR: {est_str} | IV Δ: {iv_str} | Z: {z_str} | {atr_str} Range
🧠 Conf: {confidence} | ⚡ Urgency: {urgency} | 💵 P/L: {pl_str}"""

        # ───── Send to Discord ─────
        payload = {"content": message}
        response = requests.post(webhook_url, json=payload)

        if response.status_code == 204:
            print(f"{ticker} ✅ Alert sent")
        else:
            print(f"{ticker} ❌ Failed — Status: {response.status_code}, Response: {response.text}")

    except Exception as e:
        print(f"{row.get('Ticker', 'UNKNOWN')} error: {e}")