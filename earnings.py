import yfinance as yf
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Set up Google Sheets credentials
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("your_service_account.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Earnings Calendar").sheet1  # Change to your sheet name

# Tickers to check
tickers = ["AAPL", "MSFT", "GOOG", "NVDA"]

rows = [["Ticker", "Next Earnings Date"]]
for ticker in tickers:
    stock = yf.Ticker(ticker)
    cal = stock.calendar
    try:
        next_earnings = cal.loc["Earnings Date"].values[0].date()
    except Exception:
        next_earnings = "N/A"
    rows.append([ticker, str(next_earnings)])

# Update Sheet
sheet.clear()
sheet.append_rows(rows)