"""
NSE Data Pipeline
Downloads and cleans historical price data for Indian stocks.
This is the foundation of the entire system.
"""

import os
import time
import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path
from datetime import datetime


# ── Nifty 50 symbols ──────────────────────────────────────────────
NIFTY50 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "BHARTIARTL.NS", "INFY.NS", "SBIN.NS", "LT.NS",
    "HINDUNILVR.NS", "ITC.NS", "KOTAKBANK.NS", "AXISBANK.NS",
    "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS", "HCLTECH.NS",
    "NTPC.NS", "ONGC.NS", "JSWSTEEL.NS", "TATASTEEL.NS",
    "POWERGRID.NS", "ULTRACEMCO.NS", "NESTLEIND.NS",
    "TECHM.NS", "BAJAJFINSV.NS", "DRREDDY.NS",
    # Additional Nifty 50 stocks
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS",
    "BAJAJ-AUTO.NS", "BEL.NS", "BPCL.NS", "BRITANNIA.NS",
    "CIPLA.NS", "COALINDIA.NS", "DIVISLAB.NS",
    "EICHERMOT.NS", "GRASIM.NS", "HDFCLIFE.NS",
    "HEROMOTOCO.NS", "HINDALCO.NS", "INDUSINDBK.NS",
    "M&M.NS", "SBILIFE.NS", "SHRIRAMFIN.NS",
    "TATACONSUM.NS", "TATAMOTORS.NS",
]

# ── Indices ────────────────────────────────────────────────────────
INDICES = ["^NSEI", "^NSEBANK"]


def download_stock(symbol: str, start: str = "2018-01-01") -> pd.DataFrame:
    """Download OHLCV data for one symbol."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, auto_adjust=True)

        if df.empty or len(df) < 100:
            print(f"  {symbol}: no data")
            return None

        # Standardise columns
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["open", "high", "low", "close", "volume"]

        # Add derived columns
        df["returns"]      = df["close"].pct_change()
        df["log_returns"]  = np.log(df["close"] / df["close"].shift(1))
        df["dollar_vol"]   = df["close"] * df["volume"]

        # Remove bad rows
        df = df[df["close"] > 0]
        df = df[df["high"] >= df["low"]]
        df = df.dropna(subset=["returns"])

        print(f"  {symbol}: {len(df)} days ✓")
        return df

    except Exception as e:
        print(f"  {symbol}: error — {e}")
        return None


def download_universe(
    symbols: list = None,
    save_dir: str = "data/raw",
    start: str = "2018-01-01"
) -> dict:
    """
    Download data for all symbols and save locally.
    Returns dict of {symbol: dataframe}
    """
    symbols = symbols or NIFTY50 + INDICES
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    universe = {}
    print(f"\nDownloading {len(symbols)} symbols...")
    print("-" * 40)

    for symbol in symbols:
        df = download_stock(symbol, start=start)
        if df is not None:
            # Save to CSV
            filename = symbol.replace("^", "IDX_")
            df.to_csv(f"{save_dir}/{filename}.csv")
            universe[symbol] = df
        time.sleep(0.3)  # be nice to yfinance

    print("-" * 40)
    print(f"Done: {len(universe)}/{len(symbols)} symbols downloaded")
    return universe


def load_universe(data_dir: str = "data/raw") -> dict:
    """Load all saved CSV files into a dictionary."""
    universe = {}
    path = Path(data_dir)

    if not path.exists():
        print(f"No data found at {data_dir}. Run download_universe() first.")
        return {}

    for csv_file in sorted(path.glob("*.csv")):
        symbol = csv_file.stem.replace("IDX_", "^")
        df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
        universe[symbol] = df

    print(f"Loaded {len(universe)} symbols from {data_dir}")
    return universe


def validate(symbol: str, df: pd.DataFrame) -> dict:
    """Check data quality for one stock."""
    returns = df["returns"].dropna()
    return {
        "symbol":        symbol,
        "days":          len(df),
        "start":         str(df.index[0].date()),
        "end":           str(df.index[-1].date()),
        "missing":       f"{df['close'].isna().mean()*100:.2f}%",
        "annual_return": f"{returns.mean()*252*100:.1f}%",
        "annual_vol":    f"{returns.std()*np.sqrt(252)*100:.1f}%",
    }


if __name__ == "__main__":
    # Download top 10 Nifty 50 + indices
    universe = download_universe()

    # Validate first 3
    print("\nData quality check:")
    for sym, df in list(universe.items())[:3]:
        report = validate(sym, df)
        for k, v in report.items():
            print(f"  {k}: {v}")
        print()