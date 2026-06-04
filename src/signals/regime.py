"""
Regime Detector
Identifies what kind of market we are in right now.

Four regimes:
  TRENDING_UP    → use momentum strategy
  TRENDING_DOWN  → go defensive or short
  MEAN_REVERTING → use mean reversion strategy
  HIGH_VOL       → reduce all positions, wait

This is why mean reversion and momentum both exist —
each one gets used only when conditions favour it.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum


class Regime(Enum):
    TRENDING_UP    = "trending_up"
    TRENDING_DOWN  = "trending_down"
    MEAN_REVERTING = "mean_reverting"
    HIGH_VOL       = "high_vol"
    UNKNOWN        = "unknown"


@dataclass
class RegimeResult:
    regime:        Regime
    confidence:    float      # 0.0 to 1.0
    trend_score:   float      # positive = up, negative = down
    vol_score:     float      # higher = more volatile
    mr_score:      float      # higher = more mean-reverting
    recommended_strategy: str

    def display(self):
        emoji = {
            Regime.TRENDING_UP:    "📈",
            Regime.TRENDING_DOWN:  "📉",
            Regime.MEAN_REVERTING: "↔️",
            Regime.HIGH_VOL:       "⚡",
            Regime.UNKNOWN:        "❓",
        }
        print(f"\n{'='*45}")
        print(f"  CURRENT MARKET REGIME")
        print(f"{'='*45}")
        print(f"  Regime     : {emoji[self.regime]} "
              f"{self.regime.value.upper()}")
        print(f"  Confidence : {self.confidence*100:.0f}%")
        print(f"  Trend      : {self.trend_score:+.3f}")
        print(f"  Volatility : {self.vol_score:.3f}")
        print(f"  Mean-Rev   : {self.mr_score:.3f}")
        print(f"  Use this   : {self.recommended_strategy}")
        print(f"{'='*45}")


def detect_regime(
    index_returns: pd.Series,
    window_short:  int = 20,
    window_long:   int = 60,
    vol_threshold: float = 0.20,
    trend_threshold: float = 0.02,
) -> RegimeResult:
    """
    Detect current market regime from index returns.

    Uses three indicators:
      1. Trend strength  — is the market going somewhere?
      2. Volatility      — how wild is it?
      3. Mean reversion  — does it keep bouncing back?

    index_returns: daily returns of Nifty 50 (^NSEI)
    """
    if len(index_returns) < window_long:
        return RegimeResult(
            regime=Regime.UNKNOWN,
            confidence=0.0,
            trend_score=0.0,
            vol_score=0.0,
            mr_score=0.0,
            recommended_strategy="wait — not enough data"
        )

    recent = index_returns.iloc[-window_long:]
    short  = index_returns.iloc[-window_short:]

    # ── 1. Trend score ────────────────────────────────────────────
    # Positive = trending up, Negative = trending down
    # Compare short-term momentum vs long-term momentum
    short_momentum = short.mean() * 252
    long_momentum  = recent.mean() * 252
    trend_score = short_momentum  # positive = bullish

    # Also check if price is above moving average
    cumulative = (1 + recent).cumprod()
    ma_ratio   = cumulative.iloc[-1] / cumulative.mean()
    trend_score = (trend_score + (ma_ratio - 1)) / 2

    # ── 2. Volatility score ───────────────────────────────────────
    # Annualised volatility of recent returns
    vol_score = recent.std() * np.sqrt(252)

    # ── 3. Mean reversion score ───────────────────────────────────
    # Measure autocorrelation — negative autocorrelation = mean reverting
    # If yesterday was up, today tends to be down = mean reverting
    if len(short) > 5:
        autocorr = short.autocorr(lag=1)
        mr_score = -autocorr  # flip sign: negative autocorr = high MR
    else:
        mr_score = 0.0

    # ── 4. Classify regime ────────────────────────────────────────
    if vol_score > vol_threshold:
        regime     = Regime.HIGH_VOL
        confidence = min((vol_score - vol_threshold) / 0.10 + 0.5, 0.95)
        strategy   = "reduce all positions — wait for calm"

    elif abs(trend_score) > trend_threshold:
        if trend_score > 0:
            regime     = Regime.TRENDING_UP
            confidence = min(abs(trend_score) / 0.10 + 0.4, 0.90)
            strategy   = "momentum strategy — buy strength"
        else:
            regime     = Regime.TRENDING_DOWN
            confidence = min(abs(trend_score) / 0.10 + 0.4, 0.90)
            strategy   = "defensive — reduce longs, consider cash"

    elif mr_score > 0.1:
        regime     = Regime.MEAN_REVERTING
        confidence = min(mr_score / 0.3 + 0.4, 0.85)
        strategy   = "mean reversion — buy oversold, sell overbought"

    else:
        regime     = Regime.UNKNOWN
        confidence = 0.3
        strategy   = "mixed signals — trade small size only"

    return RegimeResult(
        regime=regime,
        confidence=confidence,
        trend_score=trend_score,
        vol_score=vol_score,
        mr_score=mr_score,
        recommended_strategy=strategy,
    )


def rolling_regimes(
    index_returns: pd.Series,
    window: int = 60,
) -> pd.DataFrame:
    """
    Compute regime for every day in history.
    Shows how regime changed over time.
    Useful for understanding which strategy to use when.
    """
    results = []

    for i in range(window, len(index_returns)):
        hist = index_returns.iloc[:i]
        r    = detect_regime(hist)
        results.append({
            "date":       index_returns.index[i],
            "regime":     r.regime.value,
            "confidence": r.confidence,
            "trend":      r.trend_score,
            "vol":        r.vol_score,
            "mr_score":   r.mr_score,
        })

    df = pd.DataFrame(results).set_index("date")
    return df


def regime_strategy_map(regime: Regime) -> dict:
    """
    Given a regime, return strategy parameters.
    This is what connects the regime detector to the signal engine.
    """
    maps = {
        Regime.TRENDING_UP: {
            "strategy":    "momentum",
            "signal_fn":   "momentum_20d",
            "position_size": 1.0,
            "stop_loss":   -0.05,
        },
        Regime.TRENDING_DOWN: {
            "strategy":    "defensive",
            "signal_fn":   None,
            "position_size": 0.3,
            "stop_loss":   -0.03,
        },
        Regime.MEAN_REVERTING: {
            "strategy":    "mean_reversion",
            "signal_fn":   "mean_rev_20d",
            "position_size": 1.0,
            "stop_loss":   -0.05,
        },
        Regime.HIGH_VOL: {
            "strategy":    "cash",
            "signal_fn":   None,
            "position_size": 0.0,
            "stop_loss":   None,
        },
        Regime.UNKNOWN: {
            "strategy":    "reduced",
            "signal_fn":   "mean_rev_20d",
            "position_size": 0.5,
            "stop_loss":   -0.03,
        },
    }
    return maps.get(regime, maps[Regime.UNKNOWN])


if __name__ == "__main__":
    from src.data.pipeline import load_universe

    print("Loading data...")
    universe = load_universe()

    if "^NSEI" not in universe:
        print("Nifty index not found. Make sure ^NSEI downloaded.")
    else:
        nifty = universe["^NSEI"]

        # ── Current regime ────────────────────────────────────────
        print("\nDetecting current market regime...")
        result = detect_regime(nifty["returns"].dropna())
        result.display()

        # ── Strategy recommendation ───────────────────────────────
        params = regime_strategy_map(result.regime)
        print(f"\nStrategy parameters:")
        for k, v in params.items():
            print(f"  {k}: {v}")

        # ── Historical regimes ────────────────────────────────────
        print("\nComputing historical regimes...")
        history = rolling_regimes(nifty["returns"].dropna())

        print("\nRegime distribution (all time):")
        dist = history["regime"].value_counts()
        total = len(history)
        for regime, count in dist.items():
            pct = count / total * 100
            bar = "█" * int(pct / 2)
            print(f"  {regime:18s}: {bar} {pct:.1f}%")

        print("\nLast 10 days regime:")
        print(history[["regime", "confidence",
                        "trend", "vol"]].tail(10).round(3))