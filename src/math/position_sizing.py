"""
Position Sizing Engine
Determines HOW MUCH to invest in each trade.

This is as important as signal quality.
A great signal with wrong position size loses money.
A mediocre signal with correct position size survives.

Methods:
  1. ATR-based sizing    — adjusts for stock volatility
  2. Kelly criterion     — mathematically optimal fraction
  3. VIX-based scaling   — reduces size in volatile markets
  4. Confidence-weighted — bigger size for stronger signals
"""

import numpy as np
import pandas as pd


def atr_position_size(
    account_value:    float,
    atr:              float,
    risk_per_trade:   float = 0.01,
    atr_multiplier:   float = 2.0,
) -> dict:
    """
    ATR-based position sizing.

    Risk a fixed % of account per trade.
    Stop loss = entry price ± (ATR × multiplier)
    Position size = risk_amount / stop_distance

    Example:
      Account: ₹10,00,000
      Risk per trade: 1% = ₹10,000
      ATR: ₹50, multiplier: 2 → stop = ₹100 away
      Position size = ₹10,000 / ₹100 = 100 shares

    account_value:  total capital in ₹
    atr:            14-day average true range in ₹
    risk_per_trade: fraction of account to risk (0.01 = 1%)
    atr_multiplier: stop loss distance in ATR units
    """
    risk_amount    = account_value * risk_per_trade
    stop_distance  = atr * atr_multiplier

    if stop_distance <= 0:
        return {"shares": 0, "capital": 0, "risk": 0}

    shares         = risk_amount / stop_distance
    capital_needed = shares * stop_distance * 10  # approx

    return {
        "shares":        int(shares),
        "stop_distance": stop_distance,
        "risk_amount":   risk_amount,
        "method":        "ATR",
    }


def kelly_position_size(
    account_value: float,
    win_rate:      float,
    avg_win:       float,
    avg_loss:      float,
    fraction:      float = 0.25,
) -> dict:
    """
    Kelly Criterion — mathematically optimal position size.

    Full Kelly is too aggressive for real trading.
    We use fractional Kelly (25% of full Kelly).

    Formula:
      Kelly % = (win_rate × avg_win - loss_rate × avg_loss)
                / avg_win

    fraction: 0.25 = quarter Kelly (safer, recommended)

    win_rate: historical win rate (e.g. 0.53)
    avg_win:  average winning trade return (e.g. 0.02 = 2%)
    avg_loss: average losing trade return (e.g. 0.01 = 1%)
    """
    if avg_win <= 0 or avg_loss <= 0:
        return {"fraction": 0, "capital": 0}

    loss_rate   = 1 - win_rate
    full_kelly  = (win_rate * avg_win - loss_rate * avg_loss) \
                  / avg_win
    frac_kelly  = full_kelly * fraction
    frac_kelly  = max(0, min(frac_kelly, 0.20))  # cap at 20%

    capital = account_value * frac_kelly

    return {
        "full_kelly":   full_kelly,
        "frac_kelly":   frac_kelly,
        "capital":      capital,
        "method":       "Kelly",
    }


def vix_adjusted_size(
    base_size:     float,
    current_vol:   float,
    target_vol:    float = 0.15,
    min_scale:     float = 0.25,
    max_scale:     float = 1.50,
) -> dict:
    """
    Scale position size based on current volatility.

    When markets are calm (low vol):
      → increase position size (more confidence)
    When markets are volatile (high vol):
      → decrease position size (protect capital)

    This is the most important risk management rule
    in the entire system.

    current_vol: annualised volatility (e.g. 0.20 = 20%)
    target_vol:  desired portfolio volatility (15% default)
    """
    if current_vol <= 0:
        return {"scale": 1.0, "adjusted_size": base_size}

    # Inverse volatility scaling
    scale = target_vol / current_vol
    scale = np.clip(scale, min_scale, max_scale)
    adjusted = base_size * scale

    return {
        "scale":         scale,
        "adjusted_size": adjusted,
        "current_vol":   current_vol,
        "target_vol":    target_vol,
        "method":        "VIX-adjusted",
    }


def confidence_weighted_size(
    base_size:      float,
    signal_score:   float,
    checklist_pct:  float,
    promoter_score: float = 0.0,
) -> dict:
    """
    Adjust position size based on signal confidence.

    Three confidence inputs:
      signal_score:   how strong is the factor signal (0-1)
      checklist_pct:  what % of checklist steps passed (0-1)
      promoter_score: promoter buying confirmation (0-1)

    Higher confidence = larger position (up to 1.5x base)
    Lower confidence  = smaller position (down to 0.5x base)
    """
    # Weighted confidence
    confidence = (
        0.40 * min(abs(signal_score) * 10, 1.0) +
        0.40 * checklist_pct +
        0.20 * max(promoter_score, 0)
    )

    # Scale: 0.5x at zero confidence, 1.5x at full confidence
    scale = 0.5 + confidence
    scale = np.clip(scale, 0.25, 1.50)

    return {
        "confidence":    confidence,
        "scale":         scale,
        "adjusted_size": base_size * scale,
        "method":        "confidence-weighted",
    }


def compute_final_size(
    account_value:   float,
    stock_price:     float,
    atr:             float,
    current_vol:     float,
    win_rate:        float,
    signal_score:    float,
    checklist_pct:   float,
    promoter_score:  float = 0.0,
    max_position_pct: float = 0.15,
) -> dict:
    """
    Compute final position size combining all methods.

    Steps:
      1. ATR sizing    → base number of shares
      2. Kelly check   → validate it's not too large
      3. VIX adjust    → scale down if volatile
      4. Confidence    → scale up/down by signal quality
      5. Hard cap      → never exceed max_position_pct

    Returns final shares and full breakdown.
    """

    # Step 1: ATR base size
    atr_result = atr_position_size(
        account_value, atr, risk_per_trade=0.01
    )
    base_shares = atr_result["shares"]
    base_capital = base_shares * stock_price

    # Step 2: Kelly validation
    kelly_result = kelly_position_size(
        account_value,
        win_rate=win_rate,
        avg_win=0.025,
        avg_loss=0.015,
        fraction=0.25,
    )
    kelly_cap = kelly_result["capital"]

    # Step 3: VIX adjustment
    vix_result = vix_adjusted_size(
        base_capital, current_vol
    )
    vol_adjusted = vix_result["adjusted_size"]

    # Step 4: Confidence weighting
    conf_result = confidence_weighted_size(
        vol_adjusted, signal_score,
        checklist_pct, promoter_score
    )
    final_capital = conf_result["adjusted_size"]

    # Step 5: Hard caps
    max_capital = account_value * max_position_pct
    kelly_capital = min(kelly_cap, max_capital)
    final_capital = min(final_capital, kelly_capital)
    final_capital = max(final_capital, 0)

    final_shares  = int(final_capital / stock_price) \
                    if stock_price > 0 else 0
    final_capital = final_shares * stock_price
    pct_of_account = final_capital / account_value * 100

    return {
        "shares":          final_shares,
        "capital":         final_capital,
        "pct_of_account":  pct_of_account,
        "confidence":      conf_result["confidence"],
        "vix_scale":       vix_result["scale"],
        "conf_scale":      conf_result["scale"],
        "kelly_cap":       kelly_cap,
        "atr_base":        base_shares,
    }


def print_sizing_report(symbol: str, result: dict,
                         account_value: float):
    print(f"\n  Position Sizing: {symbol}")
    print(f"  {'─'*40}")
    print(f"  Shares          : {result['shares']:,}")
    print(f"  Capital         : ₹{result['capital']:,.0f}")
    print(f"  % of account    : {result['pct_of_account']:.1f}%")
    print(f"  Confidence      : {result['confidence']*100:.0f}%")
    print(f"  VIX scale       : {result['vix_scale']:.2f}x")
    print(f"  Confidence scale: {result['conf_scale']:.2f}x")
    print(f"  Kelly cap       : ₹{result['kelly_cap']:,.0f}")


if __name__ == "__main__":
    from src.data.pipeline import load_universe
    from src.signals.factors import mean_reversion
    from src.signals.promoter import simulate_promoter_signals

    print("Loading data...")
    universe = load_universe()
    stocks   = {k: v for k, v in universe.items()
                if not k.startswith("^")}

    # Promoter scores
    promoter = simulate_promoter_signals(list(stocks.keys()))

    ACCOUNT = 1_000_000  # ₹10 lakh

    print(f"\nAccount size: ₹{ACCOUNT:,.0f}")
    print(f"\nPosition sizing for top candidates:")
    print("=" * 50)

    # Current vol from Nifty
    nifty_vol = (
        universe["^NSEI"]["returns"]
        .dropna().iloc[-20:].std() * np.sqrt(252)
        if "^NSEI" in universe else 0.20
    )
    print(f"Current market vol: {nifty_vol*100:.1f}%")

    # Compute for all stocks
    results = []
    for sym, df in stocks.items():
        try:
            price = df["close"].iloc[-1]
            ret   = df["returns"].dropna()
            atr_val = df["returns"].abs().iloc[-14:].mean() \
                      * price

            mr    = mean_reversion(df["close"], 20)
            pr    = promoter.get(sym, 0.0)

            if np.isnan(mr) or price <= 0:
                continue

            result = compute_final_size(
                account_value  = ACCOUNT,
                stock_price    = price,
                atr            = atr_val,
                current_vol    = nifty_vol,
                win_rate       = 0.53,
                signal_score   = abs(mr),
                checklist_pct  = 0.5,
                promoter_score = pr,
            )
            result["symbol"] = sym
            result["price"]  = price
            result["mr"]     = mr
            result["promoter"] = pr
            results.append(result)

        except Exception as e:
            continue

    # Sort by confidence
    results.sort(key=lambda x: x["confidence"], reverse=True)

    print(f"\n{'Symbol':20s} {'Price':>8} {'Shares':>7} "
          f"{'Capital':>10} {'Alloc%':>7} {'Conf':>6}")
    print("-" * 62)
    for r in results[:8]:
        print(f"{r['symbol']:20s} "
              f"₹{r['price']:>7,.0f} "
              f"{r['shares']:>7,} "
              f"₹{r['capital']:>9,.0f} "
              f"{r['pct_of_account']:>6.1f}% "
              f"{r['confidence']*100:>5.0f}%")

    print("\nKey insight:")
    print("  High vol regime (20%) → VIX scale reduces positions")
    print("  Promoter buying → confidence scale increases them")
    print("  Net effect: only high-conviction trades get full size")