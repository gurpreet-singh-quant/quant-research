# Experiment Log — Session 2
**Date:** Thursday, 4 June 2026
**Change from Session 1:** Expanded universe from 11 → 30 stocks

---

## Results Comparison

| Strategy | S1 Annual | S2 Annual | S1 GT | S2 GT | S1 Verdict | S2 Verdict |
|---|---|---|---|---|---|---|
| Momentum | +11.4% | +19.4% | 0.067 | 0.416 | ❌ | ✅ |
| Mean Reversion | +18.7% | +21.3% | 1.068 | 1.381 | ✅ | ✅ |
| Combined | +7.1% | +13.4% | -0.244 | 0.520 | ❌ | ✅ |

---

## Key Finding — Universe Size Matters

Expanding from 11 to 30 stocks improved every strategy.

Why:
- More stocks = more independent signals
- Diversification reduces portfolio variance
- GT-Score improves because signal consistency
  across more stocks proves the edge is real,
  not specific to a handful of tickers

---

## 8-Step Checklist Results

Current regime: HIGH_VOL
Stocks passing checklist: 0/28

This is correct behaviour. The system correctly
refuses to trade during high volatility conditions.
Capital preservation takes priority over finding trades.

ITC.NS detailed failure:
- Step 1 FAIL: HIGH_VOL regime
- Step 3 FAIL: price 4.7% below MA50
- Step 6 FAIL: momentum -2.3% (5d) -6.3% (20d)
- Step 8 FAIL: confidence score 0.44 < 0.65

Even without the regime gate, ITC would fail
3 additional steps. The checklist is working correctly.

---

## Next Session Goals

1. Add VIX-based position sizing
2. Test mean reversion with checklist applied in backtest
3. Add promoter buying signal
4. Tune regime thresholds (mean_reverting only 1.4% of time)
5. Begin writing paper Section 3 (architecture)

---

## Paper Section 7 Update

> "Expanding the universe from 11 to 30 stocks
> transformed two previously failing strategies
> into passing ones (Momentum GT-Score 0.067→0.416,
> Combined GT-Score -0.244→0.520), confirming that
> signal robustness increases with universe size.
> This finding motivates expanding to the full
> Nifty 500 universe in future work."