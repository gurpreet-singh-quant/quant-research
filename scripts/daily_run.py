"""
Daily Run Script
This is what you run every morning before markets open.
It tells you exactly what to do today.

Run: python scripts/daily_run.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from datetime import datetime

from src.data.pipeline import load_universe, download_universe
from src.signals.factors import compute_universe_factors, rank_stocks
from src.signals.regime import detect_regime, regime_strategy_map
from src.backtest.engine import run_backtest


def daily_run(refresh_data: bool = False):
    print("\n" + "="*50)
    print(f"  QUANT RESEARCH SYSTEM")
    print(f"  {datetime.now().strftime('%A %d %B %Y — %H:%M')}")
    print("="*50)

    # ── Step 1: Load data ─────────────────────────────────────────
    print("\n[1/4] Loading market data...")
    if refresh_data:
        universe = download_universe()
    else:
        universe = load_universe()

    if not universe:
        print("No data found. Run: python -m src.data.pipeline")
        return

    # ── Step 2: Detect regime ─────────────────────────────────────
    print("\n[2/4] Detecting market regime...")
    if "^NSEI" in universe:
        nifty_returns = universe["^NSEI"]["returns"].dropna()
        regime_result = detect_regime(nifty_returns)
        regime_result.display()
        params = regime_strategy_map(regime_result.regime)
    else:
        print("  Nifty index not available")
        return

    # ── Step 3: Compute signals ───────────────────────────────────
    print("\n[3/4] Computing signals...")
    stock_universe = {
        k: v for k, v in universe.items()
        if not k.startswith("^")
    }

    factors = compute_universe_factors(stock_universe)

    # Pick signal based on regime
    from src.signals.regime import Regime
    signal_col = (
        "momentum_20d"
        if regime_result.regime == Regime.TRENDING_UP
        else "mean_rev_20d"
    )

    # ── Step 4: Generate trade recommendations ────────────────────
    print("\n[4/4] Generating recommendations...")
    pos_size = params["position_size"]

    if pos_size == 0:
        print("\n  ⚡ HIGH VOLATILITY — No trades today")
        print("  System recommendation: HOLD CASH")
        print("  Reason: volatility above threshold")
        print(f"  Current vol: {regime_result.vol_score*100:.1f}%")
        print("  Wait for: vol < 18% annualised")

    else:
        ranked = rank_stocks(factors, signal_col)

        print(f"\n  Strategy  : {params['strategy'].upper()}")
        print(f"  Signal    : {signal_col}")
        print(f"  Position  : {pos_size*100:.0f}% of capital per stock")
        print(f"  Stop loss : {params['stop_loss']*100:.0f}%")

        print(f"\n  TOP 3 — BUY candidates:")
        print(f"  {'Stock':20s} {'Signal':>10} {'RSI':>8} "
              f"{'Vol Trend':>12}")
        print(f"  {'-'*52}")

        count = 0
        for sym, row in ranked.iterrows():
            if sym.startswith("^"):
                continue

            rsi_val = factors.loc[sym, "rsi_14"] \
                if "rsi_14" in factors.columns else np.nan
            vol_val = factors.loc[sym, "volume_trend_20d"] \
                if "volume_trend_20d" in factors.columns else np.nan
            sig_val = row[signal_col] \
                if signal_col in row.index else np.nan

            # Apply basic filters
            if pd.isna(rsi_val) or pd.isna(sig_val):
                continue

            # For mean reversion: want oversold (RSI < 45)
            # For momentum: want not overbought (RSI < 70)
            rsi_ok = (rsi_val < 45
                      if "mean_rev" in signal_col
                      else rsi_val < 70)

            marker = "  ✅" if rsi_ok else "  ⚠️"
            print(f"{marker} {sym:18s} {sig_val:>10.4f} "
                  f"{rsi_val:>8.1f} {vol_val:>12.2f}")
            count += 1
            if count >= 5:
                break

        print(f"\n  BOTTOM 3 — AVOID (weakest signal):")
        print(f"  {'Stock':20s} {'Signal':>10} {'RSI':>8}")
        print(f"  {'-'*40}")
        count = 0
        for sym, row in ranked.iloc[::-1].iterrows():
            if sym.startswith("^"):
                continue
            sig_val = row[signal_col] \
                if signal_col in row.index else np.nan
            rsi_val = factors.loc[sym, "rsi_14"] \
                if "rsi_14" in factors.columns else np.nan
            print(f"  ❌ {sym:18s} {sig_val:>10.4f} {rsi_val:>8.1f}")
            count += 1
            if count >= 3:
                break

    # ── Summary ───────────────────────────────────────────────────
    print("\n" + "="*50)
    print("  SYSTEM SUMMARY")
    print("="*50)
    print(f"  Stocks monitored : {len(stock_universe)}")
    print(f"  Current regime   : {regime_result.regime.value}")
    print(f"  Regime confidence: {regime_result.confidence*100:.0f}%")
    print(f"  Action           : {params['strategy'].upper()}")
    print("="*50)
    print("\nDone. Run again tomorrow morning.")


if __name__ == "__main__":
    import sys
    refresh = "--refresh" in sys.argv
    daily_run(refresh_data=refresh)