import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# Define scope and credentials file
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcreds.json", scope)
client = gspread.authorize(creds)

# Open your sheet by name (or use .open_by_key for exact ID)
sheet = client.open("Earnings Tracker").sheet1  # Make sure the name matches your Sheet title

# Example DataFrame
df = pd.DataFrame({
    "Ticker": ["AAPL", "MSFT", "NVDA"],
    "Next Earnings": ["2024-07-25", "2024-07-30", "2024-08-28"],
    "Setup": ["Straddle", "Vertical Call", "Iron Condor"]
})

# Upload to sheet (overwrite from top-left)
sheet.clear()
sheet.update([df.columns.values.tolist()] + df.values.tolist())

print("✅ Sheet updated successfully.")