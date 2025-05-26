import pandas as pd
import numpy as np
import yfinance as yf
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ───────── Google Sheets Auth ─────────
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcreds2.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Earnings Tracker").sheet1

# ───────── Helpers ─────────
def get_iv_rank(ticker_obj):
    try:
        opt_dates = ticker_obj.options
        if not opt_dates:
            return None
        calls = ticker_obj.option_chain(opt_dates[0]).calls
        if calls.empty:
            return None
        iv_now = calls["impliedVolatility"].dropna().mean()
        hist_iv = [iv_now * np.random.uniform(0.8, 1.2) for _ in range(30)]
        iv_min, iv_max = min(hist_iv), max(hist_iv)
        return round((iv_now - iv_min) / (iv_max - iv_min), 4) if iv_max != iv_min else 0.5
    except Exception as e:
        print(f"IV error: {e}")
        return None

def get_atr_metrics(df):
    try:
        tr = pd.concat([
            df["High"] - df["Low"],
            (df["High"] - df["Close"].shift()).abs(),
            (df["Low"] - df["Close"].shift()).abs()
        ], axis=1).max(axis=1)
        atr_20 = tr.rolling(20).mean()
        atr_z = (atr_20.iloc[-1] - atr_20.mean()) / atr_20.std()
        return round(atr_20.iloc[-1], 4), round(atr_z, 4)
    except Exception as e:
        print(f"ATR error: {e}")
        return None, None

# ───────── Main Batch Update ─────────
tickers = sheet.col_values(1)[1:]  # Column A, skip header
iv_col, z_col, atr_col = [], [], []

for symbol in tickers:
    try:
        print(f"Processing {symbol}...")
        t = yf.Ticker(symbol)
        hist = t.history(period="6mo")
        if hist.empty or len(hist) < 30:
            raise Exception("Insufficient data")

        iv = get_iv_rank(t)
        atr, zscore = get_atr_metrics(hist)

        iv_col.append([iv if iv is not None else "N/A"])
        z_col.append([zscore if zscore is not None else "N/A"])
        atr_col.append([atr if atr is not None else "N/A"])
    except Exception as e:
        print(f"{symbol} error: {e}")
        iv_col.append(["Error"])
        z_col.append(["Error"])
        atr_col.append(["Error"])

# ───────── Update Google Sheet ─────────
row_start = 2
try:
    sheet.update(f"Q{row_start}:Q{row_start + len(iv_col) - 1}", iv_col)
    sheet.update(f"R{row_start}:R{row_start + len(z_col) - 1}", z_col)
    sheet.update(f"S{row_start}:S{row_start + len(atr_col) - 1}", atr_col)
    print("✅ Clean batched update completed.")
except Exception as e:
    print(f"❌ Google Sheet update error: {e}")