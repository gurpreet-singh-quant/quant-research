"""
Ablation Study — Corrected
Tests how much each component contributes to performance.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.data.pipeline import load_universe
from src.signals.factors import mean_reversion
from src.backtest.engine import run_backtest, compute_metrics
from src.backtest.statistics import full_statistical_report


def run_ablation(universe: dict):
    """Run all ablation configurations and collect results."""

    nifty = universe["^NSEI"]["returns"].dropna()
    results = []

    # ── Config 1: Benchmark ───────────────────────────────────────
    nm = compute_metrics(nifty)
    results.append({
        "config":        "Buy & Hold Nifty 50",
        "annual_return": nm["annual_return"],
        "sharpe":        (nm["annual_return"] - 0.065) / nm["annual_vol"],
        "max_dd":        nm["max_drawdown"],
        "win_rate":      nm["win_rate"],
        "gt_score":      None,
    })

    # ── Config 2: Base mean reversion ────────────────────────────
    def base_signal(df):
        return -mean_reversion(df["close"], 20)

    r2 = run_backtest(universe, base_signal,
                      name="Base MR", top_n=5, max_weight=0.15)
    results.append({
        "config":        "Base Mean Reversion",
        "annual_return": r2.annual_return,
        "sharpe":        r2.sharpe_ratio,
        "max_dd":        r2.max_drawdown,
        "win_rate":      r2.win_rate,
        "gt_score":      r2.gt_score,
    })

    # ── Config 3: + Corrected regime filter ──────────────────────
    # CORRECTED: mean reversion works BETTER in moderate/high vol
    # Only block extreme vol (>40%) and strong uptrends
    def regime_signal(df):
        mr = -mean_reversion(df["close"], 20)
        if np.isnan(mr) or len(df) < 60:
            return np.nan
        ret = df["returns"].dropna().iloc[-60:]
        vol = ret.std() * np.sqrt(252)
        if vol > 0.40:                                    # block crashes
            return np.nan
        mom60 = df["close"].iloc[-1] / df["close"].iloc[-60] - 1
        if mom60 > 0.15:                                  # block uptrends
            return np.nan
        return mr

    r3 = run_backtest(universe, regime_signal,
                      name="MR + Regime", top_n=5, max_weight=0.15)
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
        if np.isnan(mr) or len(df) < 60:
            return np.nan
        ret = df["returns"].dropna().iloc[-60:]
        vol = ret.std() * np.sqrt(252)
        if vol > 0.40:
            return np.nan
        mom60 = df["close"].iloc[-1] / df["close"].iloc[-60] - 1
        if mom60 > 0.15:
            return np.nan
        avg_vol  = df["volume"].iloc[-20:].mean()
        curr_vol = df["volume"].iloc[-1]
        if curr_vol < avg_vol * 0.8:                     # low volume → skip
            return np.nan
        return mr

    r4 = run_backtest(universe, vol_signal,
                      name="MR + Regime + Vol", top_n=5, max_weight=0.15)
    results.append({
        "config":        "MR + Regime + Volume",
        "annual_return": r4.annual_return,
        "sharpe":        r4.sharpe_ratio,
        "max_dd":        r4.max_drawdown,
        "win_rate":      r4.win_rate,
        "gt_score":      r4.gt_score,
    })

    # ── Config 5: + RSI filter (Full AMIOS) ──────────────────────
    def full_signal(df):
        mr = -mean_reversion(df["close"], 20)
        if np.isnan(mr) or len(df) < 60:
            return np.nan
        ret = df["returns"].dropna().iloc[-60:]
        vol = ret.std() * np.sqrt(252)
        if vol > 0.40:
            return np.nan
        mom60 = df["close"].iloc[-1] / df["close"].iloc[-60] - 1
        if mom60 > 0.15:
            return np.nan
        avg_vol  = df["volume"].iloc[-20:].mean()
        curr_vol = df["volume"].iloc[-1]
        if curr_vol < avg_vol * 0.8:
            return np.nan
        # RSI filter — oversold preferred for mean reversion
        delta = df["close"].diff()
        gain  = delta.clip(lower=0).iloc[-14:].mean()
        loss  = -delta.clip(upper=0).iloc[-14:].mean()
        rsi   = 100 - (100 / (1 + gain / loss)) if loss > 0 else 100
        if rsi > 70:                                     # not overbought
            return np.nan
        return mr

    r5 = run_backtest(universe, full_signal,
                      name="Full AMIOS", top_n=5, max_weight=0.15)
    results.append({
        "config":        "Full AMIOS (All Filters)",
        "annual_return": r5.annual_return,
        "sharpe":        r5.sharpe_ratio,
        "max_dd":        r5.max_drawdown,
        "win_rate":      r5.win_rate,
        "gt_score":      r5.gt_score,
    })

    return pd.DataFrame(results), {
        "base":   r2,
        "regime": r3,
        "vol":    r4,
        "full":   r5,
        "nifty":  nifty,
    }


def plot_all_figures(bt: dict, nifty: pd.Series,
                     universe: dict,
                     save_path: str = "research/figures"):
    """Generate Figures 1-4 for the paper."""
    Path(save_path).mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        "Adaptive Market Intelligence OS — Performance Analysis\n"
        "Gurpreet Singh, B.Tech AI/ML, Akal University, 2026",
        fontsize=12, fontweight="bold"
    )

    colors = {
        "full":   "#1D9E75",
        "base":   "#378ADD",
        "regime": "#F5A623",
        "nifty":  "#888780",
    }
    labels = {
        "full":   "Full AMIOS",
        "base":   "Base Mean Reversion",
        "regime": "MR + Regime Filter",
        "nifty":  "Buy & Hold Nifty 50",
    }

    # ── Figure 1: Equity curves ───────────────────────────────────
    ax1 = axes[0, 0]
    ax1.set_title("Figure 1: Equity Curves (₹10L initial capital)",
                  fontsize=10)
    for key, color in colors.items():
        if key == "nifty":
            equity = (1 + nifty).cumprod()
        else:
            equity = bt[key].equity_curve
        ax1.plot(equity.index, equity * 1_000_000,
                 label=labels[key], color=color,
                 linewidth=2.0 if key == "full" else 1.0,
                 alpha=0.9 if key == "full" else 0.6)
    ax1.set_ylabel("Portfolio Value (₹)")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)
    ax1.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, p: f"₹{x/1e5:.0f}L"))

    # ── Figure 2: Drawdown ────────────────────────────────────────
    ax2 = axes[0, 1]
    ax2.set_title("Figure 2: Drawdown — Full AMIOS vs Nifty",
                  fontsize=10)
    for key, color in [("full", "#E74C3C"), ("nifty", "#888780")]:
        if key == "nifty":
            eq = (1 + nifty).cumprod()
        else:
            eq = bt[key].equity_curve
        peak = eq.cummax()
        dd   = (eq - peak) / peak
        ax2.fill_between(dd.index, dd * 100, 0,
                         color=color, alpha=0.4,
                         label=f"{labels[key]} (max {dd.min()*100:.1f}%)")
    ax2.set_ylabel("Drawdown (%)")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # ── Figure 3: Return distribution (fat tails) ─────────────────
    ax3 = axes[1, 0]
    ax3.set_title(
        "Figure 3: Fat Tails — Student-t vs Gaussian (RELIANCE.NS)",
        fontsize=10)
    from scipy import stats as scipy_stats
    ret = universe["RELIANCE.NS"]["returns"].dropna()
    ax3.hist(ret * 100, bins=80, density=True,
             alpha=0.5, color="#378ADD", label="Actual returns")
    x   = np.linspace(ret.min() * 100, ret.max() * 100, 300)
    g   = scipy_stats.norm.pdf(x, ret.mean()*100, ret.std()*100)
    nu, mu, sigma = scipy_stats.t.fit(ret)
    t   = scipy_stats.t.pdf(x/100, nu, mu, sigma) / 100
    ax3.plot(x, g, "r-",  lw=2, label="Gaussian")
    ax3.plot(x, t, "g-",  lw=2, label=f"Student-t (ν={nu:.1f})")
    ax3.set_xlabel("Daily Return (%)")
    ax3.set_ylabel("Density")
    ax3.legend(fontsize=8)
    ax3.set_xlim(-8, 8)
    ax3.grid(True, alpha=0.3)

    # ── Figure 4: Regime timeline ─────────────────────────────────
    ax4 = axes[1, 1]
    ax4.set_title("Figure 4: Market Regime Timeline (2018-2026)",
                  fontsize=10)
    from src.signals.regime import detect_regime
    nifty_ret = universe["^NSEI"]["returns"].dropna()
    regime_colors = {
        "trending_up":    "#1D9E75",
        "trending_down":  "#E74C3C",
        "high_vol":       "#F5A623",
        "mean_reverting": "#378ADD",
        "unknown":        "#CCCCCC",
    }
    dates, regimes = [], []
    for i in range(60, len(nifty_ret), 5):
        r = detect_regime(nifty_ret.iloc[:i])
        dates.append(nifty_ret.index[i])
        regimes.append(r.regime.value)
    rs = pd.Series(regimes, index=dates)
    for regime, color in regime_colors.items():
        mask = rs == regime
        if mask.any():
            ax4.fill_between(rs.index, 0, 1, where=mask,
                             color=color, alpha=0.7,
                             label=regime.replace("_", " ").title())
    ax4.set_yticks([])
    ax4.legend(fontsize=7, loc="upper left", ncol=2)
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    path = f"{save_path}/figure_performance.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")
    return path


if __name__ == "__main__":
    print("Loading data...")
    universe = load_universe()

    print("\nRunning ablation study (corrected filters)...")
    print("=" * 65)

    df_results, bt_results = run_ablation(universe)

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

    df_results.to_csv("research/ablation_results.csv", index=False)
    print("\nSaved: research/ablation_results.csv")

    print("\nGenerating figures...")
    nifty = universe["^NSEI"]["returns"].dropna()
    plot_all_figures(bt_results, nifty, universe)
    print("Done. research/figures/figure_performance.png")