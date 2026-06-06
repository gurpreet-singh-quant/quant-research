# Research Proposal

## Title
Adaptive Market Intelligence for Indian Equity Markets:
A Unified Framework Combining Regime Detection,
Microstructure Analysis, and Anti-Overfit Validation

## Applicant
Gurpreet Singh
B.Tech (H) AI/ML — Computer Science and Engineering
Akal University, Talwandi Sabo, Bathinda, Punjab
GitHub: github.com/i-miss-her-2much/quant-research
## Problem Statement

Quantitative trading research has developed sophisticated
techniques for US and European markets. These methods fail
when applied naively to Indian markets because:

1. NSE returns have fat tails (nu≈3.57) — Gaussian models
   underestimate risk by 33%, causing position sizing errors
   
2. Indian large-cap alpha is regime-dependent — momentum
   fails (GT-Score 0.067) while mean reversion succeeds
   (GT-Score 1.381) on the same dataset

3. Unique regulatory signals (SEBI promoter disclosures,
   FII/DII flows) provide predictive information not
   available in developed markets

4. Most published Indian market strategies are overfit —
   no prior work applies rigorous out-of-sample validation

## Proposed Research

I am building the Adaptive Market Intelligence OS (AMIOS),
a complete quantitative framework for NSE equity markets.

**What has been built (proof of work):**
- NSE data pipeline: 30 stocks, 2,080 trading days, 0% missing
- 16-factor signal engine validated on real price data
- GT-Score backtester: mean reversion passes (1.381),
  momentum fails (0.067) — exactly as theory predicts
- Regime detector: correctly identifies current HIGH_VOL
  market (June 2026), recommends cash preservation
- VPIN microstructure: identifies TECHM/HCLTECH as having
  strongest informed buying pressure right now
- Mathematical foundation: rough volatility, fat-tail VaR,
  dynamic correlation, Hawkes order flow

**What the research will produce:**
1. Peer-reviewed paper on GT-Score validation framework
   for emerging market strategies
2. First systematic fat-tail analysis of NSE large-caps
3. VPIN adaptation for markets without tick data
4. Open-source implementation for reproducible research

## Why This Matters

At ₹10 lakh starting capital, the validated mean reversion
strategy yields ₹2.13 lakh annual return (21.3%) with
Sharpe 0.616 — outperforming 90% of Indian mutual funds.

Scaled to ₹1 crore: ₹21.3 lakh annual return.

More importantly: the framework automatically rejects
overfit strategies before real money is deployed. This
alone has more value than any single trading signal.

## Novelty

No existing published work for Indian markets combines:
- Anti-overfit GT-Score validation
- Fat-tail risk quantification  
- Regime-conditional strategy activation
- VPIN microstructure for daily data
- Promoter disclosure signal extraction

Each element exists separately in literature.
The unified system is the contribution.

## Timeline

Month 1-2:  Expand to Nifty 500, tune regime thresholds
Month 3-4:  Integrate Zerodha API, begin paper trading
Month 5-6:  Write and submit paper to arXiv + journal
Month 7-12: Live trading validation, second paper

## Code Repository

All code is version-controlled and publicly verifiable:
github.com/i-miss-her-2much/quant-research

Every result in this proposal can be reproduced by
running: python scripts/daily_run.py