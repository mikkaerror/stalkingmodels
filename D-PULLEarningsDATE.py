import yfinance as yf
import gspread
import pandas as pd
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# ───────── Google Sheets Auth ─────────
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcreds2.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Earnings Tracker").sheet1

# ───────── Get tickers ─────────
tickers = sheet.col_values(1)[1:]  # Column A, skip header

# ───────── Build batch update for Column D ─────────
updates = []

for symbol in tickers:
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.get_earnings_dates(limit=10)

        if isinstance(df, pd.DataFrame) and not df.empty:
            df.index = pd.to_datetime(df.index).tz_localize(None)
            today = pd.Timestamp.today().normalize()
            upcoming = df[df.index >= today]

            if not upcoming.empty:
                next_earning = upcoming.index.min().strftime("%Y-%m-%d")
                updates.append([next_earning])
                print(f"{symbol}: {next_earning}")
            else:
                updates.append(["N/A"])
                print(f"{symbol}: No future earnings")
        else:
            updates.append(["N/A"])
            print(f"{symbol}: No earnings data")
    except Exception as e:
        print(f"{symbol} error: {e}")
        updates.append(["Error"])

# ───────── Push updates to column D (4th column) ─────────
cell_range = f"D2:D{len(tickers)+1}"
sheet.update(cell_range, updates)
print("✅ Column D updated with upcoming earnings dates")