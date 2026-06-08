"""
Backtesting Engine
Tests trading strategies on historical data.
Uses GT-Score to prevent overfitting — the most important
mathematical concept in the entire system.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Callable


@dataclass
class BacktestResult:
    """Complete results from one backtest run."""
    strategy_name:   str
    annual_return:   float
    annual_vol:      float
    sharpe_ratio:    float
    max_drawdown:    float
    win_rate:        float
    total_trades:    int
    gt_score:        float
    equity_curve:    pd.Series

    def display(self):
        print(f"\n{'='*45}")
        print(f"  {self.strategy_name}")
        print(f"{'='*45}")
        print(f"  Annual return   : {self.annual_return*100:+.1f}%")
        print(f"  Annual vol      : {self.annual_vol*100:.1f}%")
        print(f"  Sharpe ratio    : {self.sharpe_ratio:.3f}")
        print(f"  Max drawdown    : {self.max_drawdown*100:.1f}%")
        print(f"  Win rate        : {self.win_rate*100:.1f}%")
        print(f"  Total trades    : {self.total_trades}")
        print(f"  GT-Score        : {self.gt_score:.3f}")
        verdict = (
            "✅ PASS — strategy is real"
            if self.gt_score > 0.3
            else "❌ FAIL — likely overfit"
        )
        print(f"  Verdict         : {verdict}")
        print(f"{'='*45}")


def compute_metrics(returns: pd.Series,
                    risk_free: float = 0.065) -> dict:
    """Compute all performance metrics from a return series."""
    if len(returns) < 10:
        return {}

    ann_return = returns.mean() * 252
    ann_vol    = returns.std() * np.sqrt(252)
    sharpe     = (ann_return - risk_free) / ann_vol \
                 if ann_vol > 0 else 0.0

    equity   = (1 + returns).cumprod()
    peak     = equity.cummax()
    drawdown = (equity - peak) / peak
    max_dd   = drawdown.min()
    win_rate = (returns > 0).mean()

    return {
        "annual_return": ann_return,
        "annual_vol":    ann_vol,
        "sharpe_ratio":  sharpe,
        "max_drawdown":  max_dd,
        "win_rate":      win_rate,
        "equity_curve":  equity,
    }


def gt_score(in_sample_returns: pd.Series,
             out_sample_returns: pd.Series,
             penalty: float = 0.5) -> float:
    """
    GT-Score: Generalization-aware objective.

    Rewards strategies that work both in-sample AND out-of-sample.
    Penalizes strategies that look great in backtest but fail live.

    GT-Score > 0.3  → strategy is likely real
    GT-Score < 0.0  → strategy is overfit, discard it
    """
    def sharpe(r):
        if len(r) < 10 or r.std() == 0:
            return 0.0
        return (r.mean() * 252) / (r.std() * np.sqrt(252))

    is_sharpe  = sharpe(in_sample_returns)
    oos_sharpe = sharpe(out_sample_returns)

    overfit_gap = max(0.0, is_sharpe - oos_sharpe)
    return oos_sharpe - penalty * overfit_gap


def run_backtest(
    universe:         dict,
    signal_fn:        Callable,
    name:             str   = "Strategy",
    train_pct:        float = 0.7,
    transaction_cost: float = 0.001,
    top_n:            int   = 5,
    max_weight:       float = 0.15,
) -> BacktestResult:
    """
    Run a full walk-forward backtest.

    signal_fn:        function(df) → float signal score
    train_pct:        fraction of data for in-sample
    transaction_cost: round-trip cost (0.1% default)
    top_n:            number of stocks to hold at any time
    max_weight:       maximum weight per stock (15% default)
                      prevents concentration in single names
    """

    # ── Align all stocks to same dates ───────────────────────────
    all_returns = pd.DataFrame({
        sym: df["returns"]
        for sym, df in universe.items()
        if "returns" in df.columns
    }).dropna()

    if len(all_returns) < 100:
        raise ValueError("Not enough data for backtest")

    n     = len(all_returns)
    split = int(n * train_pct)

    portfolio_returns = []
    dates            = []
    trades           = 0
    prev_positions   = set()

    print(f"\nRunning backtest: {name}")
    print(f"  Period:     {all_returns.index[0].date()} → "
          f"{all_returns.index[-1].date()}")
    print(f"  In-sample:  {all_returns.index[0].date()} → "
          f"{all_returns.index[split].date()}")
    print(f"  OOS:        {all_returns.index[split].date()} → "
          f"{all_returns.index[-1].date()}")
    print(f"  Universe:   {len(all_returns.columns)} stocks")
    print(f"  Top-N:      {top_n} | Max weight: {max_weight*100:.0f}%")

    # ── Walk-forward day by day ───────────────────────────────────
    for i in range(60, n):
        day_scores = {}

        for sym, df in universe.items():
            if sym not in all_returns.columns:
                continue
            hist = df.iloc[:i]
            if len(hist) < 60:
                continue
            try:
                score = signal_fn(hist)
                if not np.isnan(score):
                    day_scores[sym] = score
            except Exception:
                continue

        if not day_scores:
            continue

        # Pick top_n stocks by signal score
        ranked   = sorted(day_scores.items(),
                          key=lambda x: x[1], reverse=True)
        selected = set(s for s, _ in ranked[:top_n])

        trades += len(
            selected.symmetric_difference(prev_positions))
        prev_positions = selected

        if selected:
            # Equal-weight capped at max_weight
            n_stocks = len(selected)
            weight   = min(1.0 / n_stocks, max_weight)

            day_ret = sum(
                weight * all_returns.iloc[i][sym]
                for sym in selected
                if sym in all_returns.columns
            )

            # Transaction cost on turnover
            if selected != prev_positions:
                day_ret -= transaction_cost

            portfolio_returns.append(day_ret)
            dates.append(all_returns.index[i])

    if not portfolio_returns:
        raise ValueError("No returns generated")

    port = pd.Series(portfolio_returns, index=dates)

    # ── Split IS / OOS ────────────────────────────────────────────
    split_date  = all_returns.index[split]
    is_returns  = port[port.index <= split_date]
    oos_returns = port[port.index >  split_date]

    all_metrics = compute_metrics(port)
    score       = gt_score(is_returns, oos_returns)

    return BacktestResult(
        strategy_name = name,
        annual_return = all_metrics["annual_return"],
        annual_vol    = all_metrics["annual_vol"],
        sharpe_ratio  = all_metrics["sharpe_ratio"],
        max_drawdown  = all_metrics["max_drawdown"],
        win_rate      = all_metrics["win_rate"],
        total_trades  = trades,
        gt_score      = score,
        equity_curve  = all_metrics["equity_curve"],
    )


if __name__ == "__main__":
    from src.data.pipeline import load_universe
    from src.signals.factors import (momentum, mean_reversion,
                                      rsi, volume_trend)

    print("Loading data...")
    universe = load_universe()

    if not universe:
        print("No data. Run pipeline.py first.")
    else:
        def momentum_signal(df):
            return momentum(df["close"], window=20)

        result1 = run_backtest(
            universe, momentum_signal,
            name="20-Day Momentum",
            top_n=5, max_weight=0.15,
        )
        result1.display()

        def mean_rev_signal(df):
            mr = mean_reversion(df["close"], window=20)
            return -mr if not np.isnan(mr) else np.nan

        result2 = run_backtest(
            universe, mean_rev_signal,
            name="Mean Reversion",
            top_n=5, max_weight=0.15,
        )
        result2.display()

        def combined_signal(df):
            mom = momentum(df["close"], 20)
            vol = volume_trend(df["volume"], 20)
            r   = rsi(df["close"], 14)
            if any(np.isnan(x) for x in [mom, vol, r]):
                return np.nan
            rsi_filter = 1.0 if r < 65 else 0.5
            return mom * vol * rsi_filter

        result3 = run_backtest(
            universe, combined_signal,
            name="Combined (Momentum + Volume + RSI)",
            top_n=5, max_weight=0.15,
        )
        result3.display()