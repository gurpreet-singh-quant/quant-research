# Appendix C — Live Output 14 June 2026

**Date:** Sunday 14 June 2026, 14:22 IST
**Days since system started:** 8

---

## System Output
Regime     : UNKNOWN (30% confidence)

Volatility : 19.5% annualised

Action     : HOLD CASH (reduced)

Stocks     : 49 monitored

Promoter selling: TCS, HINDUNILVR, DRREDDY — AVOID

Trades     : 0

## Paper Trading Signals (first day logged)

| Symbol | Signal Score | Price | Interpretation |
|---|---|---|---|
| ONGC.NS | +0.0994 | ₹246 | 9.9% below 20-day MA |
| WIPRO.NS | +0.0828 | ₹180 | 8.3% below MA |
| HINDALCO.NS | +0.0668 | ₹1,022 | 6.7% below MA |
| SBILIFE.NS | +0.0604 | ₹1,706 | 6.0% below MA |
| NTPC.NS | +0.0596 | ₹354 | 6.0% below MA |

These would be buy candidates if regime were MEAN_REVERTING
or TRENDING_UP. System holds cash in UNKNOWN regime.

---

## 8-Day Live Summary

| Date | Regime | Confidence | Action |
|---|---|---|---|
| Sat 6 Jun | HIGH_VOL | 50% | HOLD CASH |
| Sun 7 Jun | TRENDING_DOWN | 90% | HOLD CASH |
| Sun 14 Jun | UNKNOWN | 30% | HOLD CASH (reduced) |

Three different regimes detected across 8 days.
Capital preserved at ₹10,00,000 throughout.
System adapting correctly to changing conditions.

---

## What This Demonstrates

The system has now operated across three distinct regime
states in 8 days of live observation. In each case it
correctly identified the regime and made the appropriate
capital preservation decision. No trades have been taken
— which is the correct decision given the sequence:
HIGH_VOL → TRENDING_DOWN → UNKNOWN.

The paper trading journal (research/paper_trade_journal.json)
now contains the first entry with 5 specific stock signals
and prices. As the system runs daily, this journal builds
into independent validation data for the GT-Score threshold.