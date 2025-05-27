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

# ───────── ATR% Z-Score Function ─────────
def atr_percent_zscore(ticker, lookback=20):
    try:
        df = yf.Ticker(ticker).history(period="2mo", interval="1d")
        if len(df) < lookback + 5:
            return "N/A"

        df["TR"] = np.maximum(
            df["High"] - df["Low"],
            np.maximum(abs(df["High"] - df["Close"].shift()), abs(df["Low"] - df["Close"].shift()))
        )
        df["ATR"] = df["TR"].rolling(window=14).mean()
        df["ATR%"] = df["ATR"] / df["Close"] * 100

        recent = df["ATR%"].dropna()[-lookback:]
        if len(recent) < lookback:
            return "N/A"

        mean = recent.mean()
        std = recent.std()
        today = recent.iloc[-1]
        z_score = (today - mean) / std if std > 0 else 0
        return round(z_score, 4)
    except Exception as e:
        print(f"Error for {ticker}: {e}")
        return "N/A"

# ───────── Collect Data ─────────
atr_zscores = [atr_percent_zscore(t) for t in tickers]

# ───────── Batch Write to Google Sheets (Column Q) ─────────
cell_range = f'Q2:Q{len(atr_zscores)+1}'
cell_list = sheet.range(cell_range)

for cell, val in zip(cell_list, atr_zscores):
    cell.value = val

try:
    sheet.update_cells(cell_list)
    print("ATR% Z-Score successfully written to Column Q.")
except APIError as e:
    print(f"Google API Error: {e}")