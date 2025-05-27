import gspread
import yfinance as yf
import numpy as np
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

# ───────── Google Sheets Auth ─────────
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcreds2.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Earnings Tracker").sheet1
tickers = sheet.col_values(1)[1:]

# ───────── Helper Functions ─────────
def safe_number(val):
    try:
        return round(val.item() if hasattr(val, 'item') else float(val), 4)
    except Exception:
        return "N/A"

def calculate_atr(df, window=14):
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window).mean()

# ───────── Process All Tickers and Build Result ─────────
output = []

for symbol in tickers:
    try:
        df = yf.download(symbol, period="6mo", interval="1d", progress=False, auto_adjust=True)
        df.dropna(inplace=True)

        # ATR% Calculation
        atr = calculate_atr(df)
        atr_pct = (atr.iloc[-1] / df["Close"].iloc[-1]) * 100 if not atr.empty else "N/A"

        # IV Rank Calculation (approximation)
        stock = yf.Ticker(symbol)
        if not stock.options:
            raise Exception("No option chain available")

        # Take current expiry (front month)
        expiry = stock.options[0]
        chain = stock.option_chain(expiry)
        all_iv = pd.concat([
            chain.calls['impliedVolatility'].dropna(),
            chain.puts['impliedVolatility'].dropna()
        ])
        iv_now = all_iv.mean()
        iv_min = all_iv.min()
        iv_max = all_iv.max()

        # IV Rank = (Current IV - Min IV) / (Max IV - Min IV)
        iv_rank = ((iv_now - iv_min) / (iv_max - iv_min)) * 100 if (iv_max - iv_min) != 0 else 50

        output.append([safe_number(atr_pct), safe_number(iv_rank)])

    except Exception as e:
        print(f"{symbol} error: {e}")
        output.append(["N/A", "N/A"])

# ───────── Batch Update to Google Sheet ─────────
cell_range = f"B2:C{len(tickers)+1}"
sheet.update(cell_range, output)
print("✅ Sheet updated successfully")