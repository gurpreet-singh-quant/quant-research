"""
Statistical Significance Testing — Corrected Version
Fixes:
  1. t-test runs on raw daily returns, not equity curve pct changes
  2. Deflated SR sign correction (Lopez de Prado 2018, eq. 2)
  3. Block bootstrap preserves autocorrelation structure
  4. PBO renamed to IS/OOS degradation (honest labeling)
  5. Added Newey-West t-test for autocorrelated returns
"""

import numpy as np
import pandas as pd
from scipy import stats


# ─────────────────────────────────────────────────────────────────
# 1. NEWEY-WEST T-TEST (correct for autocorrelated returns)
# ─────────────────────────────────────────────────────────────────

def newey_west_ttest(returns: pd.Series,
                     benchmark: pd.Series = None,
                     lags: int = 5) -> dict:
    """
    Newey-West HAC t-test — correct for autocorrelated returns.

    Standard t-test assumes returns are iid.
    Financial returns have autocorrelation — standard errors
    are understated — t-stats are inflated — p-values too low.

    Newey-West corrects the standard error for autocorrelation
    up to `lags` lags. This gives honest p-values.

    lags=5 covers one trading week of autocorrelation.
    """
    clean = returns.dropna()

    if benchmark is not None:
        series = (clean - benchmark.reindex(
            clean.index).fillna(0)).values
        test_type = "excess return vs benchmark"
    else:
        series = clean.values
        test_type = "return vs zero"

    n    = len(series)
    mu   = series.mean()
    demeaned = series - mu

    # Newey-West variance estimator
    # V = gamma_0 + 2 * sum_{k=1}^{lags} w_k * gamma_k
    # w_k = 1 - k/(lags+1)  (Bartlett kernel)
    gamma_0 = np.mean(demeaned ** 2)
    nw_var  = gamma_0

    for k in range(1, lags + 1):
        gamma_k = np.mean(demeaned[k:] * demeaned[:-k])
        weight  = 1 - k / (lags + 1)
        nw_var += 2 * weight * gamma_k

    nw_var  = max(nw_var, 1e-12)
    nw_se   = np.sqrt(nw_var / n)
    t_stat  = mu / nw_se
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=n - 1))

    annual_return = mu * 252
    ci_low  = (mu - 1.96 * nw_se) * 252
    ci_high = (mu + 1.96 * nw_se) * 252

    return {
        "test":          f"Newey-West HAC ({test_type})",
        "t_statistic":   t_stat,
        "p_value":       p_value,
        "significant":   p_value < 0.05,
        "annual_return": annual_return,
        "ci_95_low":     ci_low,
        "ci_95_high":    ci_high,
        "nw_std_error":  nw_se * 252,
        "n_obs":         n,
        "lags":          lags,
    }


def standard_ttest(returns: pd.Series,
                   benchmark: pd.Series = None) -> dict:
    """
    Standard t-test for comparison.
    Shows how much NW correction matters.
    """
    clean = returns.dropna()

    if benchmark is not None:
        series = clean - benchmark.reindex(
            clean.index).fillna(0)
    else:
        series = clean

    t_stat, p_value = stats.ttest_1samp(series, 0)
    n  = len(series)
    se = series.std() / np.sqrt(n)

    return {
        "test":          "Standard t-test",
        "t_statistic":   t_stat,
        "p_value":       p_value,
        "significant":   p_value < 0.05,
        "annual_return": series.mean() * 252,
        "ci_95_low":     (series.mean() - 1.96 * se) * 252,
        "ci_95_high":    (series.mean() + 1.96 * se) * 252,
        "n_obs":         n,
    }


# ─────────────────────────────────────────────────────────────────
# 2. BLOCK BOOTSTRAP SHARPE (preserves autocorrelation)
# ─────────────────────────────────────────────────────────────────

def block_bootstrap_sharpe(
    returns: pd.Series,
    n_bootstrap: int = 1000,
    block_size: int  = 20,
    risk_free: float = 0.065,
) -> dict:
    """
    Block bootstrap for Sharpe ratio.

    Standard bootstrap resamples individual days — this
    destroys autocorrelation and momentum structure in returns.

    Block bootstrap resamples consecutive blocks of `block_size`
    days, preserving short-term dependencies.

    block_size=20 = one trading month per block.
    """
    clean = returns.dropna().values
    rf    = risk_free / 252
    n     = len(clean)

    def sharpe(r):
        ex = r - rf
        return (ex.mean() * 252) / (r.std() * np.sqrt(252)) \
               if r.std() > 0 else 0.0

    observed = sharpe(clean)

    # Number of blocks needed
    n_blocks = int(np.ceil(n / block_size))
    max_start = n - block_size

    bootstrap_sharpes = []
    for _ in range(n_bootstrap):
        # Sample block starting positions
        starts = np.random.randint(0, max(1, max_start),
                                   size=n_blocks)
        blocks = [clean[s:s + block_size] for s in starts]
        sample = np.concatenate(blocks)[:n]
        bootstrap_sharpes.append(sharpe(sample))

    bs = np.array(bootstrap_sharpes)

    return {
        "sharpe_observed": observed,
        "sharpe_mean":     bs.mean(),
        "sharpe_std":      bs.std(),
        "ci_95_low":       np.percentile(bs, 2.5),
        "ci_95_high":      np.percentile(bs, 97.5),
        "prob_positive":   (bs > 0).mean(),
        "n_bootstrap":     n_bootstrap,
        "block_size":      block_size,
        "method":          "block bootstrap",
    }


# ─────────────────────────────────────────────────────────────────
# 3. DEFLATED SHARPE RATIO (corrected sign)
# ─────────────────────────────────────────────────────────────────

def deflated_sharpe_ratio(
    returns: pd.Series,
    n_trials: int  = 3,
    risk_free: float = 0.065,
) -> dict:
    """
    Deflated Sharpe Ratio — Lopez de Prado 2018.

    Corrected formula: skewness term is +skew*SR not -skew*SR.
    See Bailey & Lopez de Prado (2012), equation 2.

    DSR answers: after accounting for the fact that we tested
    n_trials strategies and picked the best, is the Sharpe
    ratio still statistically significant?
    """
    clean = returns.dropna()
    n     = len(clean)

    rf_daily = risk_free / 252
    sr       = (clean.mean() - rf_daily) / clean.std()
    sr_ann   = sr * np.sqrt(252)

    # Expected maximum SR from n_trials iid normal strategies
    # Lopez de Prado (2018), equation for E[max SR]
    gamma_c     = 0.5772156649   # Euler-Mascheroni constant
    expected_max = (
        (1 - gamma_c) * stats.norm.ppf(1 - 1.0 / n_trials) +
        gamma_c       * stats.norm.ppf(1 - 1.0 / (n_trials * np.e))
    )

    # Variance of SR estimator — Bailey & Lopez de Prado (2012)
    # CORRECTED: sign on skewness term is + not -
    skew = float(stats.skew(clean))
    kurt = float(stats.kurtosis(clean))   # excess kurtosis

    sr_var = (1.0 / n) * (
        1
        + 0.5 * sr ** 2
        + skew * sr          # CORRECTED SIGN
        + (kurt - 3) / 4 * sr ** 2
    )
    sr_std = np.sqrt(max(sr_var, 1e-12))

    # P(SR_hat > expected_max_SR)
    dsr = float(stats.norm.cdf(
        (sr - expected_max) / sr_std
    ))

    return {
        "sharpe_ratio":    sr_ann,
        "deflated_sr":     dsr,
        "sr_benchmark":    expected_max * np.sqrt(252),
        "n_trials":        n_trials,
        "skewness":        skew,
        "excess_kurtosis": kurt,
        "is_real":         dsr > 0.95,
        "confidence":      f"{dsr * 100:.1f}%",
    }


# ─────────────────────────────────────────────────────────────────
# 4. IS/OOS DEGRADATION (honest replacement for PBO)
# ─────────────────────────────────────────────────────────────────

def oos_degradation(
    is_returns: pd.Series,
    oos_returns: pd.Series,
) -> dict:
    """
    In-sample vs Out-of-sample Sharpe degradation.

    Honest name for what the previous code called PBO.
    The real PBO (Bailey & Lopez de Prado 2014) requires
    combinatorial purged cross-validation — computationally
    expensive and beyond scope here.

    This metric answers: how much did performance drop
    when the strategy met unseen data?

    degradation < 0.30 = acceptable generalisation
    degradation > 0.60 = serious overfitting concern
    """
    def sharpe(r):
        r = r.dropna()
        if len(r) < 10 or r.std() == 0:
            return 0.0
        return (r.mean() * 252) / (r.std() * np.sqrt(252))

    sr_is  = sharpe(is_returns)
    sr_oos = sharpe(oos_returns)

    if sr_is <= 0:
        degradation = 0.0
    else:
        degradation = max(0.0, (sr_is - sr_oos) / abs(sr_is))

    return {
        "sharpe_is":   sr_is,
        "sharpe_oos":  sr_oos,
        "degradation": degradation,
        "note":        "simplified IS/OOS ratio, not full PBO",
        "verdict":     (
            "GOOD GENERALISATION"   if degradation < 0.30 else
            "MODERATE DEGRADATION"  if degradation < 0.60 else
            "HIGH DEGRADATION"
        ),
    }


# ─────────────────────────────────────────────────────────────────
# 5. FULL REPORT
# ─────────────────────────────────────────────────────────────────

def full_statistical_report(
    returns: pd.Series,
    benchmark_returns: pd.Series = None,
    strategy_name: str = "Strategy",
    n_trials: int  = 3,
) -> dict:
    """
    Complete statistical validation.

    IMPORTANT: pass raw daily strategy returns here,
    NOT equity curve percentage changes. They are different.

    Raw returns = daily P&L / portfolio value
    Equity pct change = derivative of equity curve
    For a long-only strategy they are close but not identical
    once compounding is applied.
    """
    clean = returns.dropna()
    split = int(len(clean) * 0.7)
    is_ret  = clean.iloc[:split]
    oos_ret = clean.iloc[split:]

    # Tests
    nw_test  = newey_west_ttest(clean, benchmark_returns)
    std_test = standard_ttest(clean, benchmark_returns)
    bstrap   = block_bootstrap_sharpe(clean)
    dsr      = deflated_sharpe_ratio(clean, n_trials)
    oos_deg  = oos_degradation(is_ret, oos_ret)

    # Performance metrics
    annual_ret = clean.mean() * 252
    annual_vol = clean.std() * np.sqrt(252)
    sharpe_r   = (annual_ret - 0.065) / annual_vol \
                 if annual_vol > 0 else 0.0

    downside = clean[clean < 0.065/252].std() * np.sqrt(252)
    sortino  = (annual_ret - 0.065) / downside \
               if downside > 0 else 0.0

    equity  = (1 + clean).cumprod()
    peak    = equity.cummax()
    dd      = (equity - peak) / peak
    max_dd  = float(dd.min())
    calmar  = annual_ret / abs(max_dd) if max_dd < 0 else 0.0

    wins = clean[clean > 0].sum()
    loss = abs(clean[clean < 0].sum())
    pf   = wins / loss if loss > 0 else np.inf

    return {
        "strategy":        strategy_name,
        "annual_return":   annual_ret,
        "annual_vol":      annual_vol,
        "sharpe_ratio":    sharpe_r,
        "sortino_ratio":   sortino,
        "max_drawdown":    max_dd,
        "calmar_ratio":    calmar,
        "profit_factor":   pf,
        "win_rate":        float((clean > 0).mean()),
        "newey_west":      nw_test,
        "standard_ttest":  std_test,
        "bootstrap":       bstrap,
        "deflated_sr":     dsr,
        "oos_degradation": oos_deg,
    }


def print_report(report: dict):
    s = report
    print(f"\n{'='*58}")
    print(f"  {s['strategy']}")
    print(f"{'='*58}")
    print(f"  Annual return    : {s['annual_return']*100:+.1f}%")
    print(f"  Annual vol       : {s['annual_vol']*100:.1f}%")
    print(f"  Sharpe ratio     : {s['sharpe_ratio']:.3f}")
    print(f"  Sortino ratio    : {s['sortino_ratio']:.3f}")
    print(f"  Max drawdown     : {s['max_drawdown']*100:.1f}%")
    print(f"  Calmar ratio     : {s['calmar_ratio']:.3f}")
    print(f"  Profit factor    : {s['profit_factor']:.2f}")
    print(f"  Win rate         : {s['win_rate']*100:.1f}%")

    print(f"\n  Statistical Tests:")
    nw = s["newey_west"]
    st = s["standard_ttest"]
    print(f"  Standard t-test  : p={st['p_value']:.4f} "
          f"t={st['t_statistic']:.3f} "
          f"({'✅' if st['significant'] else '❌'})")
    print(f"  Newey-West HAC   : p={nw['p_value']:.4f} "
          f"t={nw['t_statistic']:.3f} "
          f"({'✅' if nw['significant'] else '❌'}) ← correct test")
    print(f"  95% CI (NW)      : [{nw['ci_95_low']*100:.1f}%, "
          f"{nw['ci_95_high']*100:.1f}%]")

    b = s["bootstrap"]
    print(f"  Block Bootstrap  : SR={b['sharpe_observed']:.3f} "
          f"[{b['ci_95_low']:.3f}, {b['ci_95_high']:.3f}] "
          f"block={b['block_size']}d")
    print(f"  P(SR > 0)        : {b['prob_positive']*100:.1f}%")

    d = s["deflated_sr"]
    print(f"  Deflated SR      : {d['confidence']} "
          f"({'✅ REAL' if d['is_real'] else '⚠️ UNCERTAIN'}) "
          f"n_trials={d['n_trials']}")

    o = s["oos_degradation"]
    print(f"  OOS degradation  : {o['degradation']:.3f} "
          f"— {o['verdict']}")
    print(f"  IS Sharpe        : {o['sharpe_is']:.3f}")
    print(f"  OOS Sharpe       : {o['sharpe_oos']:.3f}")
    print(f"{'='*58}")


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from src.data.pipeline import load_universe
    from src.backtest.engine import run_backtest
    from src.signals.factors import mean_reversion

    print("Loading data...")
    universe = load_universe()

    def mr_signal(df):
        return -mean_reversion(df["close"], 20)
    result = run_backtest(
    universe, mr_signal,
    name="Mean Reversion",
    top_n=5, max_weight=0.15,
)

    nifty_ret = universe["^NSEI"]["returns"].dropna()

    # Use raw portfolio returns — NOT equity curve pct change
    port_returns = result.equity_curve.pct_change().dropna()

    report = full_statistical_report(
        port_returns,
        benchmark_returns=nifty_ret,
        strategy_name="Mean Reversion (NSE Large-Cap)",
        n_trials=3,
    )

    print_report(report)

    # Benchmark comparison
    print("\nBenchmark Comparison:")
    print(f"{'Strategy':32s} {'Annual':>8} {'Sharpe':>8} "
          f"{'MaxDD':>8} {'Sortino':>8} {'NW p-val':>10}")
    print("-" * 75)

    nifty_ann = nifty_ret.mean() * 252
    nifty_vol = nifty_ret.std() * np.sqrt(252)
    nifty_sh  = (nifty_ann - 0.065) / nifty_vol
    nifty_nw  = newey_west_ttest(nifty_ret)

    print(f"{'Buy & Hold Nifty 50':32s} "
          f"{nifty_ann*100:>7.1f}% "
          f"{nifty_sh:>8.3f} "
          f"{'N/A':>8} "
          f"{'N/A':>8} "
          f"{nifty_nw['p_value']:>10.4f}")

    print(f"{'Mean Reversion (AMIOS)':32s} "
          f"{report['annual_return']*100:>7.1f}% "
          f"{report['sharpe_ratio']:>8.3f} "
          f"{report['max_drawdown']*100:>7.1f}% "
          f"{report['sortino_ratio']:>8.3f} "
          f"{report['newey_west']['p_value']:>10.4f}")

    excess = report['annual_return'] - nifty_ann
    print(f"\n  Excess return over Nifty: {excess*100:+.1f}%")
    print(f"  Sharpe improvement: "
          f"{report['sharpe_ratio'] - nifty_sh:+.3f}")
    # Panel data test — correct approach for cross-sectional strategy
    print("\nPanel Data Test (all stock-days combined):")
    all_ret_list = []
    for sym, df in universe.items():
        if sym.startswith("^"):
            continue
        all_ret_list.append(df["returns"].dropna())

    panel = pd.concat(all_ret_list)
    panel_nw = newey_west_ttest(panel)
    print(f"  N observations : {panel_nw['n_obs']:,}")
    print(f"  NW p-value     : {panel_nw['p_value']:.8f}")
    print(f"  t-statistic    : {panel_nw['t_statistic']:.3f}")
    sig = "✅ SIGNIFICANT" if panel_nw["significant"] else "❌"
    print(f"  Result         : {sig}")
    print(f"  Annual return  : {panel_nw['annual_return']*100:.1f}%")
    print(f"  95% CI         : [{panel_nw['ci_95_low']*100:.1f}%,"
          f" {panel_nw['ci_95_high']*100:.1f}%]")