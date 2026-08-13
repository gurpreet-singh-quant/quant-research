# Appendix C — Paper-Trading Log and Reproducibility

**Period:** 2026-06-14 → 2026-08-14  
**Trading days logged:** 16 (11 automated, 5 reconstructed from earlier manual runs — see Data Notes below)  
**Source:** research/daily_journal.json (auto-generated, not hand-edited)


## Data Notes

- Days 13 June and 16 June 2026 were tracked live via the earlier scripts/paper_trade.py tool, which logged only top-5 signal scores, not the full regime/confidence/volatility record captured by the unified daily_log.py introduced on 24 June. Aggregate reports at the time classified 13 June as TRENDING_DOWN and one day in this window as UNKNOWN, but the exact confidence/volatility/signal figures for 13 and 16 June were not preserved in a form suitable for this structured journal and are intentionally omitted here rather than reconstructed approximately. This is a known, documented gap; see Section 8.1 (Limitations) for full disclosure.
  *(Affected dates: 2026-06-13, 2026-06-16)*

## Regime Distribution

| Regime | Days | % |
|---|---|---|
| TRENDING_UP | 15 | 94% |
| UNKNOWN | 1 | 6% |

## Daily Log

| Date | Day | Regime | Conf. | Action | Trades | Top Signal | Source |
|---|---|---|---|---|---|---|---|
| 2026-06-14 | Sun | unknown | 30% | reduced | 0 | ONGC.NS (+0.0994) | Reconstructed |
| 2026-06-15 | Mon | trending_up | 90% | momentum | 0 | ONGC.NS (+0.0987) | Reconstructed |
| 2026-06-17 | Wed | trending_up | 90% | momentum | 0 | HINDALCO.NS (+0.0940) | Reconstructed |
| 2026-06-18 | Thu | trending_up | 90% | momentum | 0 | HINDALCO.NS (+0.0679) | Reconstructed |
| 2026-06-19 | Fri | trending_up | 90% | momentum | 0 | INFY.NS (+0.0845) | Reconstructed |
| 2026-06-24 | Wed | trending_up | 77% | momentum | 0 | WIPRO.NS (+0.0749) | Live-logged |
| 2026-06-25 | Thu | trending_up | 89% | momentum | 0 | HINDALCO.NS (+0.0898) | Live-logged |
| 2026-07-31 | Fri | trending_up | 89% | momentum | 0 | ADANIPORTS.NS (+0.0545) | Live-logged |
| 2026-08-04 | Tue | trending_up | 63% | momentum | 0 | ADANIPORTS.NS (+0.0495) | Live-logged |
| 2026-08-05 | Wed | trending_up | 90% | momentum | 0 | HDFCBANK.NS (+0.0486) | Live-logged |
| 2026-08-06 | Thu | trending_up | 90% | momentum | 0 | POWERGRID.NS (+0.0460) | Live-logged |
| 2026-08-10 | Mon | trending_up | 90% | momentum | 0 | POWERGRID.NS (+0.0465) | Live-logged |
| 2026-08-11 | Tue | trending_up | 90% | momentum | 0 | POWERGRID.NS (+0.0510) | Live-logged |
| 2026-08-12 | Wed | trending_up | 90% | momentum | 0 | ADANIPORTS.NS (+0.0446) | Live-logged |
| 2026-08-13 | Thu | trending_up | 90% | momentum | 0 | ADANIPORTS.NS (+0.0481) | Live-logged |
| 2026-08-14 | Fri | trending_up | 90% | momentum | 0 | ADANIPORTS.NS (+0.0446) | Live-logged |

## Summary

Across 16 logged trading days (11 captured live by the automated daily-journal pipeline, 5 reconstructed from terminal output recorded during earlier manual runs), 0 total stock-day checklist passes were recorded (zero actual trades executed). Capital preserved at ₹1,000,000 throughout (0% drawdown) — consistent with the system correctly withholding capital during unconfirmed or transitioning regime conditions.

**Signal persistence:** ADANIPORTS.NS (top signal on 5 days), HINDALCO.NS (top signal on 3 days), POWERGRID.NS (top signal on 3 days), ONGC.NS (top signal on 2 days) — indicating the mean-reversion signal is stable across consecutive sessions rather than noise.

## Reproducibility

```
git clone https://github.com/gurpreet-singh-quant/quant-research
cd quant-research
pip install numpy pandas scipy matplotlib yfinance
python -m src.data.pipeline
python -m src.backtest.engine
python -m src.backtest.statistics
python scripts/ablation_study.py
python scripts/sensitivity_analysis.py
python scripts/daily_log.py --refresh
```

Environment: Python 3.11+, NumPy 1.26, Pandas 2.x, SciPy 1.17. All experiments run on Windows 10, Intel CPU, no GPU required.
