import gspread
from oauth2client.service_account import ServiceAccountCredentials
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# ========== Google Sheets Setup ==========
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gcreds.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Earnings Tracker").sheet1
tickers = sheet.col_values(1)[1:]  # Skip header

# ========== Helper Functions ==========

def get_earnings_dates(ticker, n=20):
    try:
        tkr = yf.Ticker(ticker)
        df = tkr.get_earnings_dates(limit=n)
        if df is None or df.empty:
            return []
        dates = pd.to_datetime(df.index).tz_localize(None)
        today = pd.Timestamp.today().normalize()
        past_dates = [d for d in dates if d < today]
        return sorted(past_dates, reverse=True)[:n]
    except Exception as e:
        print(f"{ticker} error (earnings_dates): {e}")
        return []

def compute_atr(df, window=14):
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window).mean()

def fetch_nearest_price(df, date, col=None):
    idx = df.index
    if date in idx:
        val = df.loc[date][col] if col else df.loc[date]
        return float(val)
    prev_dates = [d for d in idx if d <= date]
    if prev_dates:
        nearest_date = max(prev_dates)
        val = df.loc[nearest_date][col] if col else df.loc[nearest_date]
        return float(val)
    next_dates = [d for d in idx if d > date]
    if next_dates:
        nearest_date = min(next_dates)
        val = df.loc[nearest_date][col] if col else df.loc[nearest_date]
        return float(val)
    return None

def fetch_iv_rank(ticker, date, lookback=252):
    try:
        tkr = yf.Ticker(ticker)
        option_dates = tkr.options
        if not option_dates:
            return None
        expiry = None
        for edate in option_dates:
            if pd.to_datetime(edate) > date + timedelta(days=7):
                expiry = edate
                break
        if expiry is None:
            expiry = option_dates[-1]
        chain = tkr.option_chain(expiry)
        calls = chain.calls
        price = fetch_nearest_price(yf.download(ticker, start=date - timedelta(days=10), end=date + timedelta(days=2), progress=False, auto_adjust=True), date, "Close")
        if price is None or calls.empty:
            return None
        calls["dist"] = (calls["strike"] - price).abs()
        atm_call = calls.sort_values("dist").iloc[0]
        iv_now = atm_call["impliedVolatility"]

        ivs = []
        for e in option_dates:
            try:
                if pd.to_datetime(e) < date and len(ivs) < lookback:
                    chain_hist = tkr.option_chain(e)
                    calls_hist = chain_hist.calls
                    calls_hist["dist"] = (calls_hist["strike"] - price).abs()
                    atm_hist = calls_hist.sort_values("dist").iloc[0]
                    ivs.append(atm_hist["impliedVolatility"])
            except:
                continue
        if not ivs:
            return None
        iv_rank = (iv_now - min(ivs)) / (max(ivs) - min(ivs)) if max(ivs) != min(ivs) else 0.5
        return iv_rank
    except Exception as e:
        print(f"{ticker} error (iv_rank): {e}")
        return None

# ========== Main Backtest ==========
results = []

for ticker in tickers:
    earnings_dates = get_earnings_dates(ticker, n=20)
    print(f"Running: {ticker} ({len(earnings_dates)} earnings)")
    try:
        for earn_date in earnings_dates:
            entry_date = earn_date - pd.Timedelta(days=20)
            exit_date = earn_date + pd.Timedelta(days=1)
            # Download price data for ATR and entries
            df_price = yf.download(
                ticker,
                start=entry_date - pd.Timedelta(days=30),
                end=exit_date + pd.Timedelta(days=2),
                progress=False,
                auto_adjust=True
            )
            if df_price.empty:
                print(f"{ticker} skipped: price data incomplete")
                continue
            df_price.index = pd.to_datetime(df_price.index).tz_localize(None)
            # ATR
            atr_series = compute_atr(df_price)
            atr14 = fetch_nearest_price(atr_series, entry_date)
            price_entry = fetch_nearest_price(df_price, entry_date, "Open")
            price_exit = fetch_nearest_price(df_price, exit_date, "Close")
            if price_entry is None or price_exit is None or atr14 is None:
                print(f"{ticker} skipped: could not find price/ATR at required dates")
                continue
            atr_pct = atr14 / price_entry if price_entry else None
            # IV Rank
            iv_rank = fetch_iv_rank(ticker, entry_date)
            # Example strategy selector
            if atr_pct is not None and iv_rank is not None:
                if atr_pct > 0.025 and iv_rank > 0.6:
                    strat = "Straddle"
                elif atr_pct < 0.015 and iv_rank < 0.3:
                    strat = "Iron Condor"
                else:
                    strat = "Vertical Call"
            else:
                strat = "N/A"
            pnl = (price_exit - price_entry) / price_entry if (price_entry and price_exit) else None
            results.append({
                "Ticker": ticker,
                "Earnings Date": earn_date.date(),
                "Entry Date": entry_date.date(),
                "Exit Date": exit_date.date(),
                "Entry Price": price_entry,
                "Exit Price": price_exit,
                "ATR(14)": atr14,
                "ATR%": atr_pct,
                "IV Rank": iv_rank,
                "Strategy": strat,
                "P/L": pnl
            })
    except Exception as e:
        print(f"{ticker} error: {e}")

# Save results
results_df = pd.DataFrame(results)
results_df.to_csv("earnings_strategy_backtest.csv", index=False)
print("✅ All done. Results saved to earnings_strategy_backtest.csv")