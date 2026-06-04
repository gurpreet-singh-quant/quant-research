"""
Alpha Signal Engine
Computes quantitative factors for every stock every day.
These are the mathematical signals that tell us what to trade.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def momentum(close: pd.Series, window: int = 20) -> float:
    """Price momentum — how much has price moved over window days."""
    if len(close) < window + 1:
        return np.nan
    return close.iloc[-1] / close.iloc[-window] - 1.0


def mean_reversion(close: pd.Series, window: int = 20) -> float:
    """
    Distance from moving average.
    Positive = above average (overbought).
    Negative = below average (oversold).
    """
    if len(close) < window:
        return np.nan
    ma = close.iloc[-window:].mean()
    return (close.iloc[-1] - ma) / ma


def volatility(returns: pd.Series, window: int = 20) -> float:
    """Annualised rolling volatility."""
    if len(returns) < window:
        return np.nan
    return returns.iloc[-window:].std() * np.sqrt(252)


def volume_trend(volume: pd.Series, window: int = 20) -> float:
    """
    Today's volume vs average volume.
    > 1.0 means higher than normal volume (confirms moves).
    < 1.0 means lower than normal (weak signal).
    """
    if len(volume) < window:
        return np.nan
    avg = volume.iloc[-window:].mean()
    return volume.iloc[-1] / avg if avg > 0 else np.nan


def rsi(close: pd.Series, window: int = 14) -> float:
    """
    Relative Strength Index.
    > 70 = overbought (potential sell signal).
    < 30 = oversold (potential buy signal).
    """
    if len(close) < window + 1:
        return np.nan
    delta = close.diff()
    gain = delta.clip(lower=0).iloc[-window:].mean()
    loss = -delta.clip(upper=0).iloc[-window:].mean()
    if loss == 0:
        return 100.0
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def atr(high: pd.Series, low: pd.Series,
        close: pd.Series, window: int = 14) -> float:
    """
    Average True Range — measures daily price movement size.
    Used for position sizing — bigger ATR = smaller position.
    """
    if len(close) < window + 1:
        return np.nan
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.iloc[-window:].mean()


def price_to_ma_ratio(close: pd.Series, window: int = 200) -> float:
    """
    How far price is from 200-day moving average.
    Classic trend indicator used by institutional traders.
    """
    if len(close) < window:
        return np.nan
    ma200 = close.iloc[-window:].mean()
    return close.iloc[-1] / ma200


def rolling_sharpe(returns: pd.Series, window: int = 60) -> float:
    """
    Rolling Sharpe ratio over window days.
    Measures if recent performance is risk-adjusted good.
    """
    if len(returns) < window:
        return np.nan
    r = returns.iloc[-window:]
    mean = r.mean() * 252
    std = r.std() * np.sqrt(252)
    return mean / std if std > 0 else np.nan


def compute_all_factors(df: pd.DataFrame) -> dict:
    """
    Compute all factors for one stock.
    Returns a dictionary of factor name → value.
    """
    factors = {}

    # Momentum factors (multiple timeframes)
    for w in [5, 10, 20, 60, 120]:
        factors[f"momentum_{w}d"] = momentum(df["close"], w)

    # Mean reversion
    for w in [10, 20, 50]:
        factors[f"mean_rev_{w}d"] = mean_reversion(df["close"], w)

    # Volatility
    for w in [10, 20, 60]:
        factors[f"volatility_{w}d"] = volatility(df["returns"], w)

    # Volume
    factors["volume_trend_20d"] = volume_trend(df["volume"], 20)

    # Technical indicators
    factors["rsi_14"]          = rsi(df["close"], 14)
    factors["atr_14"]          = atr(df["high"], df["low"], df["close"], 14)
    factors["price_to_ma_200"] = price_to_ma_ratio(df["close"], 200)
    factors["rolling_sharpe_60d"] = rolling_sharpe(df["returns"], 60)

    return factors


def compute_universe_factors(universe: dict) -> pd.DataFrame:
    """
    Compute factors for all stocks.
    Returns DataFrame with stocks as rows, factors as columns.
    """
    rows = []
    for symbol, df in universe.items():
        try:
            f = compute_all_factors(df)
            f["symbol"] = symbol
            rows.append(f)
        except Exception as e:
            print(f"  {symbol}: factor error — {e}")

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows).set_index("symbol")
    print(f"Computed {len(result.columns)} factors for {len(result)} stocks")
    return result


def rank_stocks(factors_df: pd.DataFrame,
                signal_col: str = "momentum_20d") -> pd.DataFrame:
    """
    Rank all stocks by a given factor.
    Returns sorted DataFrame — top = best signal.
    """
    if signal_col not in factors_df.columns:
        print(f"Column '{signal_col}' not found")
        return factors_df

    ranked = factors_df.sort_values(signal_col, ascending=False)
    ranked["rank"] = range(1, len(ranked) + 1)
    return ranked[[signal_col, "rank"] +
                  [c for c in ranked.columns
                   if c not in [signal_col, "rank"]]]


if __name__ == "__main__":
    from src.data.pipeline import load_universe

    print("Loading NSE data...")
    universe = load_universe()

    if not universe:
        print("No data found. Run pipeline.py first.")
    else:
        print("\nComputing factors...")
        factors = compute_universe_factors(universe)

        print("\nTop 5 stocks by 20-day momentum:")
        ranked = rank_stocks(factors, "momentum_20d")
        print(ranked[["momentum_20d", "rsi_14",
                       "volume_trend_20d", "rank"]].head())

        print("\nBottom 5 stocks (mean reversion candidates):")
        bottom = factors.sort_values("mean_rev_20d").head()
        print(bottom[["mean_rev_20d", "rsi_14", "momentum_20d"]])

        print("\nFactor summary:")
        print(factors.describe().round(3))