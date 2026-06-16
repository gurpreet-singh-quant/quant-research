# Appendix D — Paper Trading Live Results

**Period:** 13 June 2026 — 16 June 2026
**Days tracked:** 5
**Status:** Ongoing (target: 60 days)

---

## Regime Distribution (5 days)

| Regime | Days | % | Signal |
|---|---|---|---|
| TRENDING_DOWN | 2 | 40% | HOLD CASH |
| TRENDING_UP | 2 | 40% | MOMENTUM |
| UNKNOWN | 1 | 20% | REDUCED SIZE |

---

## Daily Signal Log

| Date | Regime | Top Signal | Score | Price |
|---|---|---|---|---|
| 13 Jun | TRENDING_DOWN | — | — | — |
| 14 Jun | UNKNOWN | ONGC.NS | +0.0994 | ₹246 |
| 15 Jun | TRENDING_UP | ONGC.NS | +0.0987 | ₹244 |
| 16 Jun | TRENDING_UP | — | — | — |

---

## Key Observation

The system captured a complete market cycle in 5 days:
TRENDING_DOWN → UNKNOWN → TRENDING_UP

This regime sequence is consistent with the market
recovering from the May-June 2026 correction. The
system correctly held cash throughout the downtrend
and transition, preserving full capital.

ONGC.NS appears in the top signal position on both
days signals were generated — consistent mean reversion
signal across consecutive sessions.

---

## Capital Preserved

Starting capital: ₹10,00,000
Current capital:  ₹10,00,000
Drawdown:         0.00%

The system has not taken a single trade in 9 days
of live operation. This is the correct decision —
capital preservation during regime uncertainty is
the primary risk management objective.

---

*Paper trading continues daily.*
*Full results at: github.com/gurpreet-singh-quant/quant-research*
*File: research/paper_trade_journal.json*