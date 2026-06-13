"""
Transaction Cost Sensitivity Analysis
Shows strategy robustness across different cost assumptions.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from src.data.pipeline import load_universe
from src.backtest.engine import run_backtest
from src.signals.factors import mean_reversion


def mr_signal(df):
    return -mean_reversion(df["close"], 20)


def run_sensitivity():
    print("Loading data...")
    universe = load_universe()

    costs = [0.0005, 0.001, 0.0025, 0.005, 0.010]
    results = []

    print("\nTransaction Cost Sensitivity Analysis")
    print("=" * 65)
    print(f"{'Cost':>8} {'Annual':>8} {'Sharpe':>8} "
          f"{'MaxDD':>8} {'GT-Score':>10}")
    print("-" * 50)

    for cost in costs:
        r = run_backtest(
            universe, mr_signal,
            name=f"MR cost={cost*100:.2f}%",
            top_n=5, max_weight=0.15,
            transaction_cost=cost,
        )
        results.append({
            "cost_pct":      cost * 100,
            "annual_return": r.annual_return * 100,
            "sharpe":        r.sharpe_ratio,
            "max_dd":        r.max_drawdown * 100,
            "gt_score":      r.gt_score,
            "passes":        r.gt_score > 0.3,
        })
        print(f"{cost*100:>7.2f}% "
              f"{r.annual_return*100:>7.1f}% "
              f"{r.sharpe_ratio:>8.3f} "
              f"{r.max_drawdown*100:>7.1f}% "
              f"{r.gt_score:>10.3f} "
              f"{'✅' if r.gt_score > 0.3 else '❌'}")

    df = pd.DataFrame(results)
    df.to_csv("research/sensitivity_results.csv", index=False)
    print("\nSaved: research/sensitivity_results.csv")

    # Breakeven cost
    passing = df[df["passes"]]
    if not passing.empty:
        max_cost = passing["cost_pct"].max()
        print(f"\nStrategy survives up to {max_cost:.2f}% "
              f"round-trip cost")
        print(f"Realistic NSE cost (0.10%): "
              f"{'✅ viable' if 0.10 <= max_cost else '❌ not viable'}")

    return df


if __name__ == "__main__":
    run_sensitivity()