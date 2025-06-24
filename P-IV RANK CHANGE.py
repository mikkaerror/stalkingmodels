import gspread
import yfinance as yf
import pandas as pd
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError
import time

# ───────── Google Sheets Auth ─────────
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcreds2.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Earnings Tracker").sheet1

# ───────── Clean Ticker List ─────────
raw_tickers = sheet.col_values(1)[1:]  # Skip header
tickers = [t.strip().replace("$", "") for t in raw_tickers if t.strip()]


# ───────── Function to Estimate IV Rank Delta ─────────
def get_iv_rank_change(ticker):
    try:
        opt = yf.Ticker(ticker)
        hist = opt.history(period="6mo", interval="1d")
        if len(hist) < 30:
            return "N/A"

        # Estimate IV via rolling volatility on daily % change (proxy)
        returns = hist["Close"].pct_change().dropna()
        iv_series = returns.rolling(window=20).std()

        # Normalize into rank form
        iv_rank = (iv_series - iv_series.min()) / (iv_series.max() - iv_series.min())
        delta = iv_rank.iloc[-1] - iv_rank.iloc[-6]  # Today - 5 days ago
        return round(delta, 4)
    except Exception as e:
        print(f"Error for {ticker}: {e}")
        return "N/A"


# ───────── Collect Data ─────────
iv_deltas = []
for t in tickers:
    iv_deltas.append(get_iv_rank_change(t))

# ───────── Batch Write to Google Sheets (Column P) ─────────
cell_range = f'P2:P{len(iv_deltas) + 1}'
cell_list = sheet.range(cell_range)

for cell, val in zip(cell_list, iv_deltas):
    cell.value = val

# Push all at once (avoids 429 error)
try:
    sheet.update_cells(cell_list)
    print("IV Rank Delta successfully written to Column P.")
except APIError as e:
    print(f"Google API Error: {e}")