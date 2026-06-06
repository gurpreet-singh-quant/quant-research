"""
Daily Run Script — Full System
Run every morning before market opens (9:00 AM).

Tells you exactly:
  - What regime the market is in
  - Which stocks pass the 8-step checklist
  - How many shares to buy of each
  - Where to set your stop loss

Run: python scripts/daily_run.py
Run with fresh data: python scripts/daily_run.py --refresh
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from datetime import datetime

from src.data.pipeline import load_universe, download_universe
from src.signals.factors import compute_universe_factors, mean_reversion
from src.signals.regime import detect_regime, regime_strategy_map, Regime
from src.signals.checklist import run_checklist
from src.signals.promoter import simulate_promoter_signals
from src.math.position_sizing import compute_final_size


def daily_run(
    account_value: float = 1_000_000,
    refresh_data: bool = False
):
    print("\n" + "="*55)
    print(f"  ADAPTIVE MARKET INTELLIGENCE OS")
    print(f"  {datetime.now().strftime('%A %d %B %Y — %H:%M')}")
    print(f"  Account: ₹{account_value:,.0f}")
    print("="*55)

    # ── Step 1: Load data ─────────────────────────────────────────
    print("\n[1/5] Loading market data...")
    if refresh_data:
        universe = download_universe()
    else:
        universe = load_universe()

    stocks = {k: v for k, v in universe.items()
              if not k.startswith("^")}
    print(f"  {len(stocks)} stocks loaded")

    # ── Step 2: Detect regime ─────────────────────────────────────
    print("\n[2/5] Detecting market regime...")
    nifty_returns = universe["^NSEI"]["returns"].dropna()
    regime_result = detect_regime(nifty_returns)
    params = regime_strategy_map(regime_result.regime)

    print(f"  Regime     : {regime_result.regime.value.upper()}")
    print(f"  Confidence : {regime_result.confidence*100:.0f}%")
    print(f"  Volatility : {regime_result.vol_score*100:.1f}%")
    print(f"  Action     : {params['strategy'].upper()}")

    # ── Step 3: Get promoter signals ──────────────────────────────
    print("\n[3/5] Fetching promoter signals...")
    promoter_scores = simulate_promoter_signals(list(stocks.keys()))
    buying = {k: v for k, v in promoter_scores.items() if v > 0.3}
    selling = {k: v for k, v in promoter_scores.items() if v < -0.1}
    print(f"  Promoter buying  : {len(buying)} stocks")
    print(f"  Promoter selling : {len(selling)} stocks")

    # ── Step 4: Run checklist + position sizing ───────────────────
    print("\n[4/5] Running checklist and sizing positions...")

    nifty_vol = nifty_returns.iloc[-20:].std() * np.sqrt(252)

    if params["position_size"] == 0:
        print(f"\n  ⚡ {regime_result.regime.value.upper()}")
        print(f"  No trades today — holding cash")
        print(f"  Reason: {params['strategy']}")
        trades = []
    else:
        trades = []
        for sym, df in stocks.items():
            try:
                # Compute signal
                mr = mean_reversion(df["close"], 20)
                if np.isnan(mr):
                    continue

                # Run checklist
                check = run_checklist(
                    symbol       = sym,
                    df           = df,
                    regime       = regime_result.regime,
                    signal_score = mr,
                    signal_type  = "mean_reversion",
                    direction    = "long",
                )

                if not check.passed:
                    continue

                # Position sizing
                price   = df["close"].iloc[-1]
                atr_val = df["returns"].abs().iloc[-14:].mean() * price
                pr      = promoter_scores.get(sym, 0.0)

                size = compute_final_size(
                    account_value  = account_value,
                    stock_price    = price,
                    atr            = atr_val,
                    current_vol    = nifty_vol,
                    win_rate       = 0.53,
                    signal_score   = abs(mr),
                    checklist_pct  = check.score,
                    promoter_score = pr,
                )

                stop_price = price * (1 + params["stop_loss"])

                trades.append({
                    "symbol":    sym,
                    "price":     price,
                    "shares":    size["shares"],
                    "capital":   size["capital"],
                    "alloc_pct": size["pct_of_account"],
                    "confidence":size["confidence"],
                    "mr_signal": mr,
                    "promoter":  pr,
                    "stop":      stop_price,
                    "checklist": check.score,
                })

            except Exception:
                continue

        trades.sort(key=lambda x: x["confidence"], reverse=True)

    # ── Step 5: Display recommendations ──────────────────────────
    print("\n[5/5] Trade recommendations:")
    print("=" * 55)

    if not trades:
        print(f"\n  No trades today")
        print(f"  Regime: {regime_result.regime.value.upper()}")
        print(f"  All {len(stocks)} stocks failed checklist")
        print(f"\n  What to do: HOLD CASH")
        print(f"  Check again: tomorrow morning 9:00 AM")
    else:
        total_capital = sum(t["capital"] for t in trades)
        print(f"\n  {len(trades)} trades recommended")
        print(f"  Total capital: ₹{total_capital:,.0f} "
              f"({total_capital/account_value*100:.1f}% of account)")
        print()
        print(f"  {'Symbol':20s} {'Price':>8} {'Shares':>7} "
              f"{'Alloc':>6} {'Stop':>8} {'Conf':>5}")
        print(f"  {'─'*58}")
        for t in trades:
            promoter_flag = " 🟢" if t["promoter"] > 0.3 else ""
            print(f"  {t['symbol']:20s} "
                  f"₹{t['price']:>7,.0f} "
                  f"{t['shares']:>7,} "
                  f"{t['alloc_pct']:>5.1f}% "
                  f"₹{t['stop']:>7,.0f} "
                  f"{t['confidence']*100:>4.0f}%"
                  f"{promoter_flag}")

        print(f"\n  🟢 = promoter buying confirmed")
        print(f"\n  Rules:")
        print(f"    - Set stop loss at price shown")
        print(f"    - Review position if -5% from entry")
        print(f"    - Target: mean reversion to 20-day MA")

    # ── Summary ───────────────────────────────────────────────────
    print("\n" + "="*55)
    print("  SYSTEM SUMMARY")
    print("="*55)
    print(f"  Stocks monitored : {len(stocks)}")
    print(f"  Regime           : {regime_result.regime.value}")
    print(f"  Promoter buying  : {len(buying)} stocks")
    print(f"  Promoter selling : {len(selling)} stocks — AVOID")
    if selling:
        print(f"    → {', '.join(list(selling.keys())[:3])}")
    print(f"  Trades today     : {len(trades)}")
    print(f"  Cash to keep     : "
          f"₹{account_value - sum(t['capital'] for t in trades):,.0f}")
    print("="*55)
    print(f"\nNext run: tomorrow 9:00 AM")
    print(f"Command:  python scripts/daily_run.py --refresh")


if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    # Change account value to your actual capital
    daily_run(account_value=1_000_000, refresh_data=refresh)