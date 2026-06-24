# Appendix C — Paper-Trading Log and Reproducibility

**Period:** 2026-06-24 → 2026-06-24  
**Trading days logged:** 1  
**Source:** research/daily_journal.json (auto-generated, not hand-edited)


## Regime Distribution

| Regime | Days | % |
|---|---|---|
| TRENDING_UP | 1 | 100% |

## Daily Log

| Date | Day | Regime | Conf. | Action | Trades | Top Signal |
|---|---|---|---|---|---|---|
| 2026-06-24 | Wed | trending_up | 77% | momentum | 0 | WIPRO.NS (+0.0749) |

## Summary

Across 1 logged trading days, 0 total stock-day checklist passes were recorded (zero actual trades executed). Capital preserved at ₹1,000,000 throughout (0% drawdown) — consistent with the system correctly withholding capital during unconfirmed or transitioning regime conditions.

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
