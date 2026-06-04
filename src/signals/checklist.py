"""
8-Step Confidence Checklist
Every trade must pass ALL 8 steps before execution.
This is the single biggest win rate improvement available.

Steps:
  1. Regime gate       — right strategy for current market
  2. Event blackout    — no RBI/earnings/expiry day
  3. Timeframe align   — daily trend confirms direction
  4. Volume confirm    — volume above average
  5. RSI filter        — not overbought/oversold extreme
  6. Momentum align    — short and long term agree
  7. Drawdown check    — stock not in severe drawdown
  8. Confidence gate   — combined score above threshold
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from datetime import datetime, date
from src.signals.regime import Regime


@dataclass
class ChecklistResult:
    passed:        bool
    score:         float      # 0.0 to 1.0
    steps_passed:  int
    steps_total:   int
    details:       dict       # step name → pass/fail + reason

    def display(self):
        icon = "✅ PASS" if self.passed else "❌ FAIL"
        print(f"\n  Checklist: {icon} "
              f"({self.steps_passed}/{self.steps_total} steps) "
              f"Score: {self.score*100:.0f}%")
        for step, result in self.details.items():
            mark = "  ✓" if result["pass"] else "  ✗"
            print(f"  {mark} {step:25s} {result['reason']}")


# ── Known event dates (add more as they occur) ────────────────────
RBI_DATES_2026 = [
    date(2026, 2, 7),
    date(2026, 4, 9),
    date(2026, 6, 6),
    date(2026, 8, 8),
    date(2026, 10, 8),
    date(2026, 12, 5),
]

# NSE monthly expiry (last Thursday of each month)
# Add as needed
EXPIRY_MONTHS_2026 = [
    date(2026, 1, 29), date(2026, 2, 26), date(2026, 3, 26),
    date(2026, 4, 30), date(2026, 5, 28), date(2026, 6, 25),
    date(2026, 7, 30), date(2026, 8, 27), date(2026, 9, 24),
    date(2026, 10, 29), date(2026, 11, 26), date(2026, 12, 31),
]


def is_event_blackout(check_date: date = None) -> tuple:
    """
    Returns (is_blackout, reason).
    Blackout = no trading on this date.
    """
    if check_date is None:
        check_date = date.today()

    # RBI policy day
    if check_date in RBI_DATES_2026:
        return True, "RBI policy day"

    # Day before RBI (uncertainty)
    from datetime import timedelta
    day_after = check_date + timedelta(days=1)
    if day_after in RBI_DATES_2026:
        return True, "day before RBI policy"

    # Monthly expiry day
    if check_date in EXPIRY_MONTHS_2026:
        return True, "monthly F&O expiry day"

    return False, "clear"


def step1_regime_gate(regime: Regime,
                       signal_type: str) -> tuple:
    """
    Step 1: Is this signal appropriate for the current regime?
    Mean reversion in trending market = wrong.
    Momentum in high vol = wrong.
    """
    compatible = {
        "mean_reversion": [Regime.MEAN_REVERTING, Regime.UNKNOWN],
        "momentum":       [Regime.TRENDING_UP],
        "defensive":      [Regime.TRENDING_DOWN,
                           Regime.HIGH_VOL, Regime.UNKNOWN],
    }

    allowed = compatible.get(signal_type, [])

    # Mean reversion also works when trending_down
    # (stocks that fell too hard bounce back)
    if signal_type == "mean_reversion" and \
       regime == Regime.TRENDING_DOWN:
        return True, f"allowed in {regime.value}"

    if regime in allowed:
        return True, f"compatible with {regime.value}"
    elif regime == Regime.HIGH_VOL:
        return False, "HIGH_VOL — no trading"
    else:
        return False, f"{regime.value} wrong for {signal_type}"


def step2_event_blackout(check_date: date = None) -> tuple:
    """Step 2: Is today a blackout date?"""
    blackout, reason = is_event_blackout(check_date)
    if blackout:
        return False, f"blackout: {reason}"
    return True, "no events today"


def step3_timeframe_align(df: pd.DataFrame,
                           direction: str = "long") -> tuple:
    """
    Step 3: Does the daily trend confirm the trade direction?
    Long trade needs: price above 50-day MA.
    Short trade needs: price below 50-day MA.
    """
    if len(df) < 50:
        return False, "insufficient history"

    ma50  = df["close"].iloc[-50:].mean()
    price = df["close"].iloc[-1]
    ratio = price / ma50

    if direction == "long":
        if ratio > 0.97:      # within 3% of MA or above
            return True, f"price/MA50 = {ratio:.3f}"
        return False, f"price below MA50 ({ratio:.3f})"
    else:
        if ratio < 1.03:
            return True, f"price/MA50 = {ratio:.3f}"
        return False, f"price above MA50 ({ratio:.3f})"


def step4_volume_confirm(df: pd.DataFrame,
                          min_ratio: float = 1.0) -> tuple:
    """
    Step 4: Is volume confirming the move?
    Volume should be at least equal to 20-day average.
    """
    if len(df) < 20:
        return False, "insufficient history"

    avg_vol  = df["volume"].iloc[-20:].mean()
    curr_vol = df["volume"].iloc[-1]

    if avg_vol == 0:
        return False, "zero average volume"

    ratio = curr_vol / avg_vol
    if ratio >= min_ratio:
        return True, f"vol ratio = {ratio:.2f}x"
    return False, f"low volume ({ratio:.2f}x avg)"


def step5_rsi_filter(df: pd.DataFrame,
                      direction: str = "long",
                      overbought: float = 70,
                      oversold: float = 30) -> tuple:
    """
    Step 5: RSI filter.
    Long: RSI not overbought (< 70).
    Mean reversion long: RSI oversold (< 45) preferred.
    """
    if len(df) < 15:
        return False, "insufficient history"

    delta = df["close"].diff()
    gain  = delta.clip(lower=0).iloc[-14:].mean()
    loss  = -delta.clip(upper=0).iloc[-14:].mean()
    rsi   = 100 - (100 / (1 + gain/loss)) if loss > 0 else 100

    if direction == "long":
        if rsi < overbought:
            return True, f"RSI = {rsi:.1f} (not overbought)"
        return False, f"RSI = {rsi:.1f} (overbought > {overbought})"
    else:
        if rsi > oversold:
            return True, f"RSI = {rsi:.1f} (not oversold)"
        return False, f"RSI = {rsi:.1f} (oversold < {oversold})"


def step6_momentum_align(df: pd.DataFrame,
                          direction: str = "long") -> tuple:
    """
    Step 6: Do short-term and medium-term momentum agree?
    Both 5-day and 20-day momentum should point same direction.
    """
    if len(df) < 21:
        return False, "insufficient history"

    mom5  = df["close"].iloc[-1] / df["close"].iloc[-5]  - 1
    mom20 = df["close"].iloc[-1] / df["close"].iloc[-20] - 1

    if direction == "long":
        # At least one positive, neither strongly negative
        if mom20 > -0.05 and mom5 > -0.03:
            return True, f"5d={mom5*100:.1f}% 20d={mom20*100:.1f}%"
        return False, f"negative momentum 5d={mom5*100:.1f}% 20d={mom20*100:.1f}%"
    else:
        if mom20 < 0.05 and mom5 < 0.03:
            return True, f"5d={mom5*100:.1f}% 20d={mom20*100:.1f}%"
        return False, f"positive momentum 5d={mom5*100:.1f}%"


def step7_drawdown_check(df: pd.DataFrame,
                          max_dd_threshold: float = -0.20) -> tuple:
    """
    Step 7: Is the stock in a severe drawdown?
    Avoid stocks down more than 20% from recent peak.
    Falling knives are hard to catch.
    """
    if len(df) < 60:
        return False, "insufficient history"

    prices  = df["close"].iloc[-60:]
    peak    = prices.cummax()
    dd      = (prices / peak - 1).iloc[-1]

    if dd > max_dd_threshold:
        return True, f"drawdown = {dd*100:.1f}%"
    return False, f"severe drawdown = {dd*100:.1f}%"


def step8_confidence_gate(score: float,
                           threshold: float = 0.65) -> tuple:
    """
    Step 8: Is the combined signal strong enough?
    Only take top signals — filter out weak ones.
    """
    if score >= threshold:
        return True, f"score {score:.3f} >= {threshold}"
    return False, f"score {score:.3f} < {threshold} threshold"


def run_checklist(
    symbol:      str,
    df:          pd.DataFrame,
    regime:      Regime,
    signal_score: float,
    signal_type: str = "mean_reversion",
    direction:   str = "long",
    check_date:  date = None,
) -> ChecklistResult:
    """
    Run all 8 steps for one stock.
    Returns ChecklistResult with pass/fail and details.
    """
    if check_date is None:
        check_date = date.today()

    steps = {}

    # Run all 8 steps
    p1, r1 = step1_regime_gate(regime, signal_type)
    steps["1. Regime gate"]      = {"pass": p1, "reason": r1}

    p2, r2 = step2_event_blackout(check_date)
    steps["2. Event blackout"]   = {"pass": p2, "reason": r2}

    p3, r3 = step3_timeframe_align(df, direction)
    steps["3. Timeframe align"]  = {"pass": p3, "reason": r3}

    p4, r4 = step4_volume_confirm(df)
    steps["4. Volume confirm"]   = {"pass": p4, "reason": r4}

    p5, r5 = step5_rsi_filter(df, direction)
    steps["5. RSI filter"]       = {"pass": p5, "reason": r5}

    p6, r6 = step6_momentum_align(df, direction)
    steps["6. Momentum align"]   = {"pass": p6, "reason": r6}

    p7, r7 = step7_drawdown_check(df)
    steps["7. Drawdown check"]   = {"pass": p7, "reason": r7}

    # Normalise signal score to 0-1 for step 8
    norm_score = min(abs(signal_score) * 10, 1.0)
    p8, r8 = step8_confidence_gate(norm_score)
    steps["8. Confidence gate"]  = {"pass": p8, "reason": r8}

    # Count passes
    passed_list  = [v["pass"] for v in steps.values()]
    steps_passed = sum(passed_list)
    steps_total  = len(steps)
    overall_score = steps_passed / steps_total

    # Must pass ALL steps
    overall_pass = all(passed_list)

    return ChecklistResult(
        passed       = overall_pass,
        score        = overall_score,
        steps_passed = steps_passed,
        steps_total  = steps_total,
        details      = steps,
    )


if __name__ == "__main__":
    from src.data.pipeline import load_universe
    from src.signals.regime import detect_regime
    from src.signals.factors import mean_reversion, rsi

    print("Loading data...")
    universe = load_universe()

    # Detect regime
    nifty  = universe["^NSEI"]
    regime = detect_regime(nifty["returns"].dropna())
    print(f"Current regime: {regime.regime.value}")

    stocks = {k: v for k, v in universe.items()
              if not k.startswith("^")}

    print(f"\nRunning checklist on {len(stocks)} stocks...")
    print("=" * 55)

    passed_stocks = []
    failed_stocks = []

    for symbol, df in stocks.items():
        print(f"  Checking {symbol}...", end="\r")

        sig = mean_reversion(df["close"], window=20)
        if np.isnan(sig):
            continue

        result = run_checklist(
            symbol       = symbol,
            df           = df,
            regime       = regime.regime,
            signal_score = sig,
            signal_type  = "mean_reversion",
            direction    = "long",
        )

        if result.passed:
            passed_stocks.append((symbol, result, sig))
        else:
            failed_stocks.append((symbol, result, sig))

    print(" " * 40)  # clear the \r line

    print(f"\n✅ PASSED ({len(passed_stocks)} stocks):")
    if passed_stocks:
        for sym, res, sig in passed_stocks:
            print(f"   {sym:20s} score={res.score:.0%} "
                  f"signal={sig:+.4f}")
    else:
        print("   None — all filtered out (expected in HIGH_VOL)")

    print(f"\n❌ FAILED ({len(failed_stocks)} stocks):")
    for sym, res, sig in failed_stocks[:5]:
        fails = [f"{k}: {v['reason']}"
                 for k, v in res.details.items()
                 if not v["pass"]]
        print(f"   {sym:20s} → {fails[0] if fails else ''}")

    print(f"\n  ... and {max(0, len(failed_stocks)-5)} more failed")

    # Detailed view of one stock
    sym = "ITC.NS"
    if sym in stocks:
        df  = stocks[sym]
        sig = mean_reversion(df["close"], window=20)
        res = run_checklist(
            sym, df, regime.regime,
            sig, "mean_reversion", "long"
        )
        print(f"\nDetailed checklist for {sym}:")
        res.display()