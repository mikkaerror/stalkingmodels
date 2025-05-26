import yfinance as yf
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ───── Google Sheets Auth ─────
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcreds2.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Earnings Tracker").sheet1

# ───── Get tickers ─────
tickers = sheet.col_values(1)[1:]  # Skip header

# ───── Helpers ─────
def compute_atr_pct(df):
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    atr_pct = atr / df["Close"]
    return atr_pct

def calc_iv_rank(current_iv, hist):
    iv_min, iv_max = min(hist), max(hist)
    return 0.5 if iv_max == iv_min else (current_iv - iv_min) / (iv_max - iv_min)

# ───── Main loop ─────
for i, ticker in enumerate(tickers, start=2):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty or "Close" not in df:
            sheet.update_cell(i, 3, "N/A")
            sheet.update_cell(i, 4, "N/A")
            continue

        atr_pct_series = compute_atr_pct(df)
        atr_pct = atr_pct_series.iloc[-1]

        hist_iv = df["Close"].pct_change().rolling(14).std().dropna() * (252 ** 0.5)
        current_iv = hist_iv.iloc[-1]
        iv_rank = calc_iv_rank(current_iv, hist_iv.tolist())

        sheet.update_cell(i, 3, round(atr_pct * 100, 2))  # ATR%
        sheet.update_cell(i, 4, round(iv_rank * 100, 2))  # IV Rank

    except Exception as e:
        print(f"{ticker} error: {e}")
        sheet.update_cell(i, 3, "Error")
        sheet.update_cell(i, 4, "Error")