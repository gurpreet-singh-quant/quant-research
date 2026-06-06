"""
Mathematical Foundations
Replaces every wrong assumption in classical finance.

Wrong → Right:
  Normal distribution   → Student-t + fat tails
  Standard Brownian     → Rough volatility (H≈0.1)
  Fixed correlation     → Dynamic correlation
  Random order flow     → Hawkes self-exciting process
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize


# ─────────────────────────────────────────────────────────────────
# 1. ROUGH VOLATILITY
# ─────────────────────────────────────────────────────────────────

class RoughVolatility:
    """
    Volatility follows fractional Brownian motion with H≈0.1.
    Standard models assume H=0.5 (smooth).
    Real markets have H≈0.1 (rough, spiky, anti-persistent).

    What this means practically:
      After a volatility spike, it tends to drop sharply.
      Standard GARCH misses this — rough vol captures it.
      Better vol forecast = better position sizing.
    """

    def __init__(self, hurst: float = 0.1):
        self.hurst = hurst
        self.theta = None   # long-run mean log-vol
        self.nu    = None   # vol of vol
        self.kappa = None   # mean reversion speed

    def estimate_hurst(self, log_vol: np.ndarray) -> float:
        """
        Estimate Hurst exponent from data.
        H < 0.5 = rough (typical for equities)
        H = 0.5 = standard Brownian motion
        H > 0.5 = trending (rare in vol)
        """
        lags = [1, 2, 4, 8, 16]
        variances = []
        for lag in lags:
            diffs = log_vol[lag:] - log_vol[:-lag]
            variances.append(np.var(diffs))

        log_lags = np.log(lags)
        log_vars = np.log(np.array(variances) + 1e-12)
        slope, _ = np.polyfit(log_lags, log_vars, 1)
        return float(np.clip(slope / 2, 0.05, 0.45))

    def fit(self, returns: pd.Series) -> "RoughVolatility":
        """Fit model to return series."""
        # Compute realized volatility
        rv = returns.rolling(21).std() * np.sqrt(252)
        rv = rv.dropna()
        log_rv = np.log(rv.clip(1e-8).values)

        self.hurst = self.estimate_hurst(log_rv)
        self.theta = float(log_rv.mean())
        self.nu    = float(log_rv.std())
        self.kappa = 5.0   # typical mean reversion speed
        return self

    def forecast(self, returns: pd.Series,
                 horizon: int = 5) -> pd.Series:
        """
        Forecast volatility for next `horizon` days.
        Returns annualised volatility forecast.

        FIX: At i = n-1, the term (n-i-1) = 0, which raises
        ZeroDivisionError when the exponent (hurst-0.5) is negative.
        We handle the boundary by omitting the second term at the
        last index — mathematically correct for the Riemann-Liouville
        fractional kernel where the boundary weight is (1)^(H-0.5).
        """
        if self.theta is None:
            self.fit(returns)

        rv = returns.rolling(21).std() * np.sqrt(252)
        log_rv = np.log(rv.dropna().clip(1e-8).values)

        exponent = self.hurst - 0.5   # always negative (~-0.4) for rough vol
        n = len(log_rv)

        # ── FIXED: guard against 0 ** negative_exponent ──────────────
        weights = np.array([
            (n - i) ** exponent - (n - i - 1) ** exponent
            if (n - i - 1) > 0
            else (n - i) ** exponent   # boundary: last point, no prior step
            for i in range(n)
        ])
        weights = np.maximum(weights, 0)   # clip any floating-point negatives
        # ─────────────────────────────────────────────────────────────

        forecasts = []
        for h in range(1, horizon + 1):
            if weights.sum() > 0:
                w = weights / weights.sum()
                weighted = np.sum(w * log_rv)
            else:
                weighted = self.theta

            decay = np.exp(-self.kappa * h / 252)
            fcast = self.theta + decay * (weighted - self.theta)
            forecasts.append(np.exp(fcast))

        return pd.Series(forecasts,
                         index=range(1, horizon + 1),
                         name="vol_forecast")

    def realized_vol(self, returns: pd.Series,
                     window: int = 21) -> pd.Series:
        """Rolling realized volatility (annualised)."""
        return returns.rolling(window).std() * np.sqrt(252)


# ─────────────────────────────────────────────────────────────────
# 2. FAT TAIL RISK MODEL
# ─────────────────────────────────────────────────────────────────

class FatTailRisk:
    """
    Real market returns have fat tails — extreme events
    happen far more often than normal distribution predicts.

    NSE small/mid caps: degrees of freedom ≈ 3-4
    This means 3x more crashes than Gaussian models predict.

    Impact: Gaussian position sizing is too aggressive.
    Fix: use Student-t VaR for correct risk measurement.
    """

    def __init__(self):
        self.nu    = 4.0    # degrees of freedom
        self.mu    = 0.0    # location
        self.sigma = 0.01   # scale

    def fit(self, returns: pd.Series) -> "FatTailRisk":
        """Fit Student-t distribution to returns."""
        clean = returns.dropna().values
        try:
            self.nu, self.mu, self.sigma = stats.t.fit(clean)
            self.nu = max(self.nu, 2.1)
        except Exception:
            pass
        return self

    def var_95(self) -> float:
        """95% Value at Risk using fat-tail model."""
        return float(stats.t.ppf(0.05, self.nu,
                                  self.mu, self.sigma))

    def cvar_95(self) -> float:
        """
        Conditional VaR (Expected Shortfall).
        Average loss on the worst 5% of days.
        More conservative than VaR.
        """
        var = self.var_95()
        # Approximate CVaR for Student-t
        alpha = 0.05
        t_val = stats.t.ppf(alpha, self.nu)
        pdf_val = stats.t.pdf(t_val, self.nu)
        cvar = -(self.mu + self.sigma *
                 (self.nu + t_val**2) /
                 (self.nu - 1) *
                 pdf_val / alpha)
        return float(cvar)

    def gaussian_vs_fattail(self, returns: pd.Series) -> dict:
        """
        Compare Gaussian VaR vs fat-tail VaR.
        Shows how much Gaussian underestimates risk.
        """
        self.fit(returns)
        gaussian_var = returns.std() * stats.norm.ppf(0.05)
        fattail_var  = self.var_95() * returns.std() / self.sigma

        return {
            "gaussian_var_95":  gaussian_var,
            "fattail_var_95":   fattail_var,
            "underestimate_pct": (fattail_var - gaussian_var)
                                  / abs(gaussian_var) * 100,
            "degrees_freedom":  self.nu,
        }


# ─────────────────────────────────────────────────────────────────
# 3. DYNAMIC CORRELATION
# ─────────────────────────────────────────────────────────────────

class DynamicCorrelation:
    """
    Correlations between stocks change over time.
    In a crisis, everything correlates to 1.0 simultaneously.
    Standard portfolio theory misses this completely.

    DCC-GARCH updates correlation matrix every day.
    This prevents holding "diversified" portfolios that
    all crash together during market stress.
    """

    def __init__(self, a: float = 0.05, b: float = 0.93):
        self.a     = a      # reaction speed to new info
        self.b     = b      # persistence of correlation
        self.Q_bar = None   # long-run correlation
        self.Q     = None   # current Q matrix

    def fit(self, returns_df: pd.DataFrame) -> "DynamicCorrelation":
        """Fit DCC model to return matrix."""
        clean = returns_df.dropna()
        std_ret = clean / (clean.std() + 1e-8)
        self.Q_bar = std_ret.cov().values
        self.Q     = self.Q_bar.copy()
        return self

    def update(self, new_returns: np.ndarray) -> np.ndarray:
        """Update correlation with today's returns."""
        if self.Q_bar is None:
            return np.eye(len(new_returns))

        eps = new_returns / (np.std(new_returns) + 1e-8)
        self.Q = ((1 - self.a - self.b) * self.Q_bar +
                  self.a * np.outer(eps, eps) +
                  self.b * self.Q)

        D = np.diag(1.0 / np.sqrt(
            np.maximum(np.diag(self.Q), 1e-8)))
        R = D @ self.Q @ D
        np.fill_diagonal(R, 1.0)
        return np.clip(R, -0.999, 0.999)

    def current_avg_correlation(self) -> float:
        """Average pairwise correlation right now."""
        if self.Q is None:
            return 0.0
        D = np.diag(1.0 / np.sqrt(
            np.maximum(np.diag(self.Q), 1e-8)))
        R = D @ self.Q @ D
        n = R.shape[0]
        off_diag = (R.sum() - n) / (n * (n - 1))
        return float(off_diag)


# ─────────────────────────────────────────────────────────────────
# 4. HAWKES PROCESS — Self-Exciting Order Flow
# ─────────────────────────────────────────────────────────────────

class HawkesOrderFlow:
    """
    Orders trigger more orders.
    One large FII sell creates a cascade of more selling.
    Detecting the cascade early gives lead time on moves.

    Branching ratio n = alpha/beta:
      n < 1: stable market (orders decay naturally)
      n → 1: critical (cascade building)
      n > 1: explosive (flash crash / squeeze)
    """

    def __init__(self, decay: float = 10.0):
        self.mu    = 1.0    # background intensity
        self.alpha = 0.5    # excitation amplitude
        self.beta  = decay  # decay rate

    def detect_cluster(self, volume: pd.Series,
                        threshold: float = 2.0) -> dict:
        """
        Detect institutional order clustering from volume.
        Returns signal and branching ratio.
        """
        if len(volume) < 5:
            return {"cluster": False,
                    "intensity": 0.0,
                    "signal": "NEUTRAL"}

        vol_z = ((volume - volume.mean()) /
                 (volume.std() + 1e-8))
        current_z = float(vol_z.iloc[-1])
        branching  = min(abs(current_z) / threshold * 0.8, 0.99)

        if current_z > threshold:
            signal = "BUY_MOMENTUM"
        elif current_z < -threshold:
            signal = "SELL_MOMENTUM"
        else:
            signal = "NEUTRAL"

        return {
            "cluster":   abs(current_z) > threshold,
            "intensity": current_z,
            "branching": branching,
            "signal":    signal,
        }

    def branching_ratio(self) -> float:
        return self.alpha / self.beta


# ─────────────────────────────────────────────────────────────────
# 5. COMBINED MATH ENGINE
# ─────────────────────────────────────────────────────────────────

class MathEngine:
    """
    Combines all mathematical models into one engine.
    Call analyze() to get complete picture for any stock.
    """

    def __init__(self):
        self.rough_vol = RoughVolatility()
        self.fat_tail  = FatTailRisk()
        self.dcc       = DynamicCorrelation()
        self.hawkes    = HawkesOrderFlow()

    def analyze(self, symbol: str,
                df: pd.DataFrame) -> dict:
        """Full mathematical analysis for one stock."""
        returns = df["returns"].dropna()
        volume  = df["volume"]

        if len(returns) < 60:
            return {"symbol": symbol, "error": "insufficient data"}

        # Rough volatility
        self.rough_vol.fit(returns)
        vol_forecast = self.rough_vol.forecast(returns, horizon=5)
        current_vol  = self.rough_vol.realized_vol(
            returns).dropna().iloc[-1]
        hurst        = self.rough_vol.hurst

        # Fat tails
        ft = self.fat_tail.gaussian_vs_fattail(returns)

        # Hawkes order flow
        hawk = self.hawkes.detect_cluster(volume.tail(20))

        # Risk score (0=safe, 1=risky)
        risk_score = min(
            0.3 * (current_vol / 0.4) +
            0.3 * (1 - hurst / 0.5) +
            0.2 * max(0, (4 - ft["degrees_freedom"]) / 4) +
            0.2 * min(abs(hawk["intensity"]) / 3, 1),
            1.0
        )

        return {
            "symbol":           symbol,
            "vol_today":        current_vol,
            "vol_5d_forecast":  float(vol_forecast.mean()),
            "hurst_exponent":   hurst,
            "fat_tail_nu":      ft["degrees_freedom"],
            "gaussian_underest": ft["underestimate_pct"],
            "hawkes_signal":    hawk["signal"],
            "hawkes_intensity": hawk["intensity"],
            "risk_score":       risk_score,
        }


if __name__ == "__main__":
    from src.data.pipeline import load_universe

    print("Loading data...")
    universe = load_universe()
    engine   = MathEngine()

    stocks = {k: v for k, v in universe.items()
              if not k.startswith("^")}

    print(f"\nMathematical analysis of {len(stocks)} stocks")
    print("=" * 65)

    results = []
    for sym, df in stocks.items():
        r = engine.analyze(sym, df)
        if "error" not in r:
            results.append(r)

    results.sort(key=lambda x: x["risk_score"])

    print(f"\n{'Symbol':20s} {'Vol':>7} {'Hurst':>7} "
          f"{'Nu':>5} {'Gauss%':>8} {'Hawkes':>12} {'Risk':>6}")
    print("-" * 70)

    for r in results:
        print(f"{r['symbol']:20s} "
              f"{r['vol_today']*100:>6.1f}% "
              f"{r['hurst_exponent']:>7.3f} "
              f"{r['fat_tail_nu']:>5.1f} "
              f"{r['gaussian_underest']:>7.1f}% "
              f"{r['hawkes_signal']:>12s} "
              f"{r['risk_score']:>6.3f}")

    print("\nKey insights:")
    safest   = results[0]
    riskiest = results[-1]
    print(f"  Safest stock   : {safest['symbol']} "
          f"(risk={safest['risk_score']:.3f})")
    print(f"  Riskiest stock : {riskiest['symbol']} "
          f"(risk={riskiest['risk_score']:.3f})")

    avg_nu = np.mean([r["fat_tail_nu"] for r in results])
    avg_underest = np.mean([r["gaussian_underest"]
                             for r in results])
    print(f"\n  Average tail thickness (nu) : {avg_nu:.2f}")
    print(f"  Gaussian underestimates risk: "
          f"{avg_underest:.1f}% on average")
    print(f"  This means standard risk models are wrong by "
          f"{avg_underest:.0f}%")