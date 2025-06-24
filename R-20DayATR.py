import gspread
import yfinance as yf
import pandas as pd
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError

# ───────── Google Sheets Auth ─────────
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcreds2.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Earnings Tracker").sheet1

# ───────── Clean Ticker List ─────────
raw_tickers = sheet.col_values(1)[1:]  # Skip header
tickers = [t.strip().replace("$", "") for t in raw_tickers if t.strip()]

# ───────── 20-Day ATR Function ─────────
def get_20day_atr(ticker):
    try:
        df = yf.Ticker(ticker).history(period="2mo", interval="1d")
        if len(df) < 22:
            return "N/A"

        df["TR"] = np.maximum(
            df["High"] - df["Low"],
            np.maximum(abs(df["High"] - df["Close"].shift()), abs(df["Low"] - df["Close"].shift()))
        )
        df["ATR_20"] = df["TR"].rolling(window=20).mean()

        latest_atr = df["ATR_20"].iloc[-1]
        return round(latest_atr, 4) if pd.notna(latest_atr) else "N/A"
    except Exception as e:
        print(f"Error for {ticker}: {e}")
        return "N/A"

# ───────── Collect Data ─────────
atr20_values = [get_20day_atr(t) for t in tickers]

# ───────── Batch Write to Google Sheets (Column R) ─────────
cell_range = f'R2:R{len(atr20_values)+1}'
cell_list = sheet.range(cell_range)

for cell, val in zip(cell_list, atr20_values):
    cell.value = val

try:
    sheet.update_cells(cell_list)
    print("20-Day ATR successfully written to Column R.")
except APIError as e:
    print(f"Google API Error: {e}")