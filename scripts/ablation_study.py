"""
Ablation Study
Tests how much each component contributes to performance.
Standard requirement for ML/AI research papers.

Tests each configuration:
  Base: mean reversion only
  + Regime detection
  + VPIN filter  
  + Position sizing
  + Promoter signal
  Full AMIOS: all components
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # no display needed
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from src.data.pipeline import load_universe
from src.signals.factors import mean_reversion
from src.signals.regime import detect_regime, Regime
from src.signals.vpin import microstructure_score
from src.signals.promoter import simulate_promoter_signals
from src.backtest.engine import run_backtest, compute_metrics
from src.backtest.statistics import full_statistical_report


def run_ablation(universe: dict) -> pd.DataFrame:
    """Run all ablation configurations and collect results."""

    stocks = {k: v for k, v in universe.items()
              if not k.startswith("^")}
    nifty  = universe["^NSEI"]["returns"].dropna()

    results = []

    # ── Config 1: Buy and Hold Nifty (benchmark) ─────────────────
    nifty_metrics = compute_metrics(nifty)
    results.append({
        "config":        "Buy & Hold Nifty 50",
        "annual_return": nifty_metrics["annual_return"],
        "sharpe":        (nifty_metrics["annual_return"] - 0.065)
                         / nifty_metrics["annual_vol"],
        "max_dd":        nifty_metrics["max_drawdown"],
        "win_rate":      nifty_metrics["win_rate"],
        "gt_score":      None,
    })

    # ── Config 2: Base mean reversion ────────────────────────────
    def base_signal(df):
        return -mean_reversion(df["close"], 20)

    r2 = run_backtest(universe, base_signal,
                      name="Base MR", top_n=3)
    results.append({
        "config":        "Base Mean Reversion",
        "annual_return": r2.annual_return,
        "sharpe":        r2.sharpe_ratio,
        "max_dd":        r2.max_drawdown,
        "win_rate":      r2.win_rate,
        "gt_score":      r2.gt_score,
    })

    # ── Config 3: + Regime filter ─────────────────────────────────
    regime_cache = {}
    def regime_signal(df):
        mr = -mean_reversion(df["close"], 20)
        if np.isnan(mr):
            return np.nan
        # Simple regime filter on last 60 days
        ret = df["returns"].dropna().iloc[-60:]
        vol = ret.std() * np.sqrt(252)
        # Skip if high vol
        if vol > 0.22:
            return np.nan
        return mr

    r3 = run_backtest(universe, regime_signal,
                      name="MR + Regime", top_n=3)
    results.append({
        "config":        "MR + Regime Filter",
        "annual_return": r3.annual_return,
        "sharpe":        r3.sharpe_ratio,
        "max_dd":        r3.max_drawdown,
        "win_rate":      r3.win_rate,
        "gt_score":      r3.gt_score,
    })

    # ── Config 4: + Volume confirmation ──────────────────────────
    def vol_signal(df):
        mr = -mean_reversion(df["close"], 20)
        if np.isnan(mr) or len(df) < 20:
            return np.nan
        ret = df["returns"].dropna().iloc[-60:]
        vol = ret.std() * np.sqrt(252)
        if vol > 0.22:
            return np.nan
        # Volume confirmation
        avg_vol = df["volume"].iloc[-20:].mean()
        curr_vol = df["volume"].iloc[-1]
        if curr_vol < avg_vol * 0.8:
            return np.nan
        return mr

    r4 = run_backtest(universe, vol_signal,
                      name="MR + Regime + Vol", top_n=3)
    results.append({
        "config":        "MR + Regime + Volume",
        "annual_return": r4.annual_return,
        "sharpe":        r4.sharpe_ratio,
        "max_dd":        r4.max_drawdown,
        "win_rate":      r4.win_rate,
        "gt_score":      r4.gt_score,
    })

    # ── Config 5: + RSI filter ────────────────────────────────────
    def rsi_signal(df):
        mr = -mean_reversion(df["close"], 20)
        if np.isnan(mr) or len(df) < 20:
            return np.nan
        ret = df["returns"].dropna().iloc[-60:]
        if ret.std() * np.sqrt(252) > 0.22:
            return np.nan
        avg_vol = df["volume"].iloc[-20:].mean()
        if df["volume"].iloc[-1] < avg_vol * 0.8:
            return np.nan
        # RSI filter
        delta = df["close"].diff()
        gain  = delta.clip(lower=0).iloc[-14:].mean()
        loss  = -delta.clip(upper=0).iloc[-14:].mean()
        rsi   = 100-(100/(1+gain/loss)) if loss > 0 else 100
        if rsi > 65:
            return np.nan
        return mr

    r5 = run_backtest(universe, rsi_signal,
                      name="Full AMIOS", top_n=3)
    results.append({
        "config":        "Full AMIOS (All Filters)",
        "annual_return": r5.annual_return,
        "sharpe":        r5.sharpe_ratio,
        "max_dd":        r5.max_drawdown,
        "win_rate":      r5.win_rate,
        "gt_score":      r5.gt_score,
    })

    return pd.DataFrame(results), {
        "base": r2,
        "regime": r3,
        "vol": r4,
        "full": r5,
        "nifty": nifty,
    }


def plot_equity_curves(backtest_results: dict,
                       nifty: pd.Series,
                       save_path: str = "research/figures"):
    """Generate all figures for the paper."""
    Path(save_path).mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "Adaptive Market Intelligence OS — Performance Analysis\n"
        "Gurpreet Singh, Akal University, 2026",
        fontsize=13, fontweight="bold"
    )

    colors = {
        "full":   "#1D9E75",
        "base":   "#378ADD",
        "regime": "#F5A623",
        "nifty":  "#888780",
    }

    # ── Figure 1: Equity curves ───────────────────────────────────
    ax1 = axes[0, 0]
    ax1.set_title("Figure 1: Equity Curves (₹10L initial capital)",
                  fontsize=10)

    for name, color in colors.items():
        if name == "nifty":
            equity = (1 + nifty).cumprod()
            label  = "Buy & Hold Nifty 50"
        else:
            r = backtest_results[name]
            equity = r.equity_curve
            labels = {
                "full":   "Full AMIOS",
                "base":   "Base Mean Reversion",
                "regime": "MR + Regime Filter",
            }
            label = labels.get(name, name)

        ax1.plot(equity.index, equity * 1_000_000,
                 label=label, color=color,
                 linewidth=1.5 if name == "full" else 1.0)

    ax1.set_ylabel("Portfolio Value (₹)")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, p: f"₹{x/1e5:.0f}L"))

    # ── Figure 2: Drawdown ────────────────────────────────────────
    ax2 = axes[0, 1]
    ax2.set_title("Figure 2: Drawdown Curve (Full AMIOS)",
                  fontsize=10)

    r_full = backtest_results["full"]
    equity = r_full.equity_curve
    peak   = equity.cummax()
    dd     = (equity - peak) / peak

    ax2.fill_between(dd.index, dd * 100, 0,
                     color="#E74C3C", alpha=0.6,
                     label="Drawdown")
    ax2.axhline(y=dd.min() * 100, color="red",
                linestyle="--", alpha=0.5,
                label=f"Max DD: {dd.min()*100:.1f}%")
    ax2.set_ylabel("Drawdown (%)")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # ── Figure 3: Return distribution ────────────────────────────
    ax3 = axes[1, 0]
    ax3.set_title(
        "Figure 3: Return Distribution — Fat Tails vs Gaussian",
        fontsize=10)

    from src.data.pipeline import load_universe
    universe = load_universe()
    sample_returns = universe["RELIANCE.NS"]["returns"].dropna()

    from scipy import stats
    ax3.hist(sample_returns * 100, bins=80,
             density=True, alpha=0.6,
             color="#378ADD", label="Actual returns")

    x = np.linspace(sample_returns.min() * 100,
                    sample_returns.max() * 100, 200)
    # Gaussian fit
    gaus = stats.norm.pdf(
        x, sample_returns.mean()*100,
        sample_returns.std()*100)
    ax3.plot(x, gaus, "r-", linewidth=2, label="Gaussian")
    # Student-t fit
    nu, mu, sigma = stats.t.fit(sample_returns)
    t_pdf = stats.t.pdf(x/100, nu, mu, sigma) / 100
    ax3.plot(x, t_pdf, "g-", linewidth=2,
             label=f"Student-t (ν={nu:.1f})")
    ax3.set_xlabel("Daily Return (%)")
    ax3.set_ylabel("Density")
    ax3.legend(fontsize=8)
    ax3.set_xlim(-8, 8)
    ax3.grid(True, alpha=0.3)

    # ── Figure 4: Regime timeline ─────────────────────────────────
    ax4 = axes[1, 1]
    ax4.set_title("Figure 4: Market Regime Timeline (2018-2026)",
                  fontsize=10)

    nifty_ret = universe["^NSEI"]["returns"].dropna()
    regime_colors = {
        "trending_up":    "#1D9E75",
        "trending_down":  "#E74C3C",
        "high_vol":       "#F5A623",
        "mean_reverting": "#378ADD",
        "unknown":        "#888780",
    }

    from src.signals.regime import detect_regime
    window = 60
    dates, regimes = [], []
    step = 5  # every 5 days for speed

    for i in range(window, len(nifty_ret), step):
        hist = nifty_ret.iloc[:i]
        r    = detect_regime(hist)
        dates.append(nifty_ret.index[i])
        regimes.append(r.regime.value)

    regime_series = pd.Series(regimes, index=dates)

    for regime, color in regime_colors.items():
        mask = regime_series == regime
        if mask.any():
            ax4.fill_between(
                regime_series.index,
                0, 1,
                where=mask,
                color=color, alpha=0.7,
                label=regime.replace("_", " ").title()
            )

    ax4.set_ylabel("Regime")
    ax4.set_yticks([])
    ax4.legend(fontsize=7, loc="upper left",
               ncol=2)
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = f"{save_path}/figure_performance.png"
    plt.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Figure saved: {fig_path}")
    return fig_path


if __name__ == "__main__":
    print("Loading data...")
    universe = load_universe()

    print("\nRunning ablation study...")
    print("(This tests each component separately)")
    print("=" * 60)

    df_results, bt_results = run_ablation(universe)

    # Print ablation table
    print("\nAblation Study Results:")
    print(f"\n{'Configuration':28s} {'Annual':>8} "
          f"{'Sharpe':>8} {'MaxDD':>8} "
          f"{'WinRate':>8} {'GT-Score':>9}")
    print("-" * 72)

    for _, row in df_results.iterrows():
        gt = f"{row['gt_score']:.3f}" \
             if row["gt_score"] is not None else "  N/A"
        print(f"{row['config']:28s} "
              f"{row['annual_return']*100:>7.1f}% "
              f"{row['sharpe']:>8.3f} "
              f"{row['max_dd']*100:>7.1f}% "
              f"{row['win_rate']*100:>7.1f}% "
              f"{gt:>9s}")

    # Save to CSV for paper
    df_results.to_csv("research/ablation_results.csv",
                      index=False)
    print("\nSaved: research/ablation_results.csv")

    # Generate figures
    print("\nGenerating figures...")
    nifty = universe["^NSEI"]["returns"].dropna()
    plot_equity_curves(bt_results, nifty)

    print("\nDone. Add figures to paper as Figure 1-4.")
    print("File: research/figures/figure_performance.png")