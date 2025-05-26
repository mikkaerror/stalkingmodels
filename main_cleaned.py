
# main_cleaned.py — Backtest Engine with ATR + IV Setup (Cleaned + Enhanced)
import datetime as dt
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from earnings_calendar2 import catalysts  # Make sure this file is in the same directory

# ───────── config ─────────
TICKERS = list(catalysts.keys())
START_DATE = "2023-01-01"
END_DATE = dt.date.today().isoformat()
MIN_ATR_PCT = 0.02
LOW_IV_RANK = 0.30
HIGH_IV_RANK = 0.60
OPTION_DTE = 30

# ───────── helpers ─────────
@lru_cache(maxsize=None)
def get_price_history(ticker: str,
                      start: str = START_DATE,
                      end: str = END_DATE) -> pd.DataFrame:
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False).dropna()
    df = df.loc[~df.index.duplicated(keep="first")]
    df = df.loc[:, ~df.columns.duplicated(keep="last")]
    return df

def compute_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window).mean()

def get_option_chain(ticker: str, as_of: dt.date) -> Tuple[pd.DataFrame, pd.DataFrame]:
    tkr = yf.Ticker(ticker)
    if not tkr.options:
        return pd.DataFrame(), pd.DataFrame()
    as_of_ts = pd.Timestamp(as_of)
    target_exp = next((exp for exp in tkr.options
                       if (pd.Timestamp(exp) - as_of_ts).days >= OPTION_DTE),
                      tkr.options[-1])
    chain = tkr.option_chain(target_exp)
    return chain.calls, chain.puts

def calc_iv_rank(current_iv: float, hist: List[float]) -> float:
    iv_min, iv_max = min(hist), max(hist)
    return 0.5 if iv_max == iv_min else (current_iv - iv_min) / (iv_max - iv_min)

# ───────── data class ─────────
@dataclass
class Trade:
    ticker: str
    open_date: pd.Timestamp
    strategy: str
    entry_price: float
    exit_price: float
    entry_iv: float
    exit_iv: float
    pnl: float

# ───────── backtest engine ─────────
def simulate_trades(ticker: str,
                    events: Dict[str, pd.Timestamp]) -> List[Trade]:
    df = get_price_history(ticker)
    df = df.loc[:, ~df.columns.duplicated(keep="last")]

    atr = compute_atr(df)
    if isinstance(atr, pd.DataFrame):
        atr = atr.iloc[:, 0]
    atr.name = "ATR14"

    close_ser = df["Close"].astype(float)
    if isinstance(close_ser, pd.DataFrame):
        close_ser = close_ser.iloc[:, 0]

    atr_pct = atr / close_ser
    atr_pct.name = "ATR_pct"

    for col in ["ATR14", "ATR_pct"]:
        if col in df.columns:
            df.drop(columns=col, inplace=True)

    df["ATR14"] = atr
    df["ATR_pct"] = atr_pct

    trades: List[Trade] = []
    iv_hist: List[float] = []

    for evt, evt_dt in events.items():
        if evt_dt not in df.index or df.index.get_loc(evt_dt) < 20:
            continue
        open_idx = df.index.get_loc(evt_dt) - 20
        open_row = df.iloc[open_idx]
        spot = float(open_row["Close"])
        atr_val = float(open_row["ATR_pct"])
        open_dt = open_row.name

        calls, _ = get_option_chain(ticker, open_dt.date())
        if calls.empty:
            continue
        atm_call = calls.iloc[(calls["strike"] - spot).abs().argsort()[:1]]
        iv_now = float(atm_call["impliedVolatility"].values[0])
        iv_hist.append(iv_now)
        iv_rank = calc_iv_rank(iv_now, iv_hist)

        if atr_val >= MIN_ATR_PCT and iv_rank <= LOW_IV_RANK:
            strat, pnl = "Long ATM Straddle", atr_val * 100
        elif atr_val >= MIN_ATR_PCT and iv_rank >= HIGH_IV_RANK:
            strat, pnl = "Iron Condor", 0.5 * atr_val * 100
        else:
            strat, pnl = "Vertical Call", 0.75 * atr_val * 100

        trades.append(
            Trade(ticker, open_dt, strat,
                  spot, spot * (1 + atr_val),
                  iv_now, iv_now * 0.8, pnl)
        )
    return trades

# ───────── main ─────────
def main():
    all_trades: List[Trade] = []
    for tk in TICKERS:
        all_trades.extend(simulate_trades(tk, catalysts.get(tk, {})))

    if not all_trades:
        print("No trades generated – tweak thresholds or events.")
        return

    res = pd.DataFrame([t.__dict__ for t in all_trades])
    print("Trade summary:")
    print(res.groupby("strategy")["pnl"].describe())

    # Additional output
    res["win"] = res["pnl"] > 0
    win_rate = res.groupby("strategy")["win"].mean()
    print("\nWin Rates:")
    print(win_rate)

    res.to_csv("backtest_results.csv", index=False)
    print("Saved to backtest_results.csv")

if __name__ == "__main__":
    main()
