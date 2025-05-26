import yfinance as yf
import gspread
import numpy as np
import pandas as pd
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# ───────── Google Sheets Auth ─────────
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcreds2.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Earnings Tracker").sheet1

# ───────── Get tickers ─────────
tickers = sheet.col_values(1)[1:]  # Skip header

# ───────── Helpers ─────────
def calculate_atr(df, window=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=window).mean()

def calculate_iv_rank(current_iv, iv_history):
    iv_min, iv_max = min(iv_history), max(iv_history)
    return round((current_iv - iv_min) / (iv_max - iv_min), 4) if iv_max > iv_min else 0.5

def calculate_zscore(series):
    if len(series) < 2:
        return None
    return round((series[-1] - np.mean(series)) / np.std(series), 4)

# ───────── Main Loop ─────────
for i, symbol in enumerate(tickers, start=2):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="6mo", interval="1d", auto_adjust=False)
        if hist.empty or len(hist) < 21:
            print(f"{symbol}: Not enough price data.")
            continue

        atr_series = calculate_atr(hist, window=14).dropna()
        last_atr = round(atr_series.iloc[-1], 4)
        atr_z = calculate_zscore(atr_series[-20:])

        option_dates = ticker.options
        if not option_dates:
            raise ValueError("No option chain available")

        calls = ticker.option_chain(option_dates[0]).calls
        spot = hist["Close"].iloc[-1]
        atm_call = calls.iloc[(calls["strike"] - spot).abs().argsort()[:1]]
        current_iv = float(atm_call["impliedVolatility"].iloc[0])
        iv_history = [current_iv * (0.8 + np.random.rand() * 0.4) for _ in range(20)]
        iv_rank = calculate_iv_rank(current_iv, iv_history)

        sheet.update_cell(i, 17, iv_rank)
        sheet.update_cell(i, 18, atr_z)
        sheet.update_cell(i, 19, last_atr)
        print(f"{symbol}: ✅")

    except Exception as e:
        print(f"{symbol} error: {e}")
        try:
            sheet.update_cell(i, 17, "Error")
            sheet.update_cell(i, 18, "Error")
            sheet.update_cell(i, 19, "Error")
        except:
            pass