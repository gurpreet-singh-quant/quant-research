# Appendix B — Live Regime Shift Detection
## Sunday 7 June 2026, 09:40 IST

---

## Regime Change Detected

| | Saturday 6 Jun | Sunday 7 Jun |
|---|---|---|
| Regime | HIGH_VOL | **TRENDING_DOWN** |
| Confidence | 50% | **90%** |
| Volatility | 20.0% | 19.9% |
| Action | CASH | DEFENSIVE |
| Promoter sell | AXISBANK, HINDUNILVR | **TCS, ITC** |

---

## What This Demonstrates

### Regime detection is dynamic
The system updated its market assessment overnight
using fresh data. Volatility dropped slightly
(20.0% → 19.9%) but the trend signal strengthened
significantly (confidence 50% → 90%).

### Promoter signals updated automatically
The selling warning changed from AXISBANK/HINDUNILVR
to TCS/ITC. The simulated promoter signal rotated
to reflect new market conditions. In production with
live SEBI data, this would reflect actual insider
transaction disclosures filed overnight.

### System correctly stays in cash
TRENDING_DOWN with 90% confidence means the market
is falling with high conviction. Deploying capital
into a confirmed downtrend would violate basic
risk management principles. The checklist correctly
blocks all 28 stocks.

### Capital fully preserved
₹10,00,000 remains in cash for the second
consecutive day. This is the correct decision.
A system that trades every day regardless of
conditions is not a risk management system —
it is a gambling machine.

---

## Two-Day Live Summary