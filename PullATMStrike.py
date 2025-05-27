import gspread
import yfinance as yf
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError
import re

# ───────── Google Sheets Auth ─────────
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcreds2.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Earnings Tracker").sheet1

# ───────── Get Tickers from Column A ─────────
raw_tickers = sheet.col_values(1)[1:]  # Skip header

def is_valid_ticker(t):
    return re.match(r'^[A-Z\-\.]{1,6}$', t) is not None  # Valid tickers only

tickers = [t.strip().replace("$", "") for t in raw_tickers if t.strip() and is_valid_ticker(t.strip().replace("$", ""))]

# ───────── Get Real ATM Strike from Option Chain ─────────
def get_real_atm_strike(ticker):
    try:
        opt = yf.Ticker(ticker)
        current_price = opt.history(period="1d")["Close"].iloc[-1]

        # Get nearest expiry date
        expirations = opt.options
        if not expirations:
            print(f"No option chain for {ticker}")
            return "N/A"

        chain = opt.option_chain(expirations[0])  # Use front-month
        all_strikes = list(chain.calls['strike'])  # Just grab strike column

        # Find closest strike to current price
        atm_strike = min(all_strikes, key=lambda x: abs(x - current_price))
        return int(round(atm_strike))  # No decimals!
    except Exception as e:
        print(f"Error retrieving {ticker}: {e}")
        return "N/A"

# ───────── Fetch Real ATM Strike Prices ─────────
strike_prices = [[get_real_atm_strike(t)] for t in tickers]

# ───────── Safe Sheet Update ─────────
start_row = 2
end_row = start_row + len(strike_prices) - 1
target_col = "AD"
required_col_count = 30

sheet.resize(rows=1000, cols=required_col_count)

try:
    sheet.update(
        range_name=f"{target_col}{start_row}:{target_col}{end_row}",
        values=strike_prices
    )
    print("✅ Real ATM strikes (rounded integers) successfully written to Column AD.")
except APIError as e:
    print(f"Google Sheets error: {e}")