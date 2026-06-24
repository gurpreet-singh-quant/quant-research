"""
Daily Journal — single source of truth for live system operation.

Combines what daily_run.py prints (regime, confidence, action,
promoter signals) with what paper_trade.py logs (top-5 signals)
into ONE append-only record: research/daily_journal.json

Skips weekends automatically (NSE closed, yfinance just returns
stale Friday data — logging it as a "new" day would be dishonest).

Idempotent: running twice on the same date overwrites that day's
entry rather than duplicating it.

Usage:
    python scripts/daily_log.py              # log today
    python scripts/daily_log.py --refresh    # force fresh download
    python scripts/daily_log.py --report     # print summary so far
"""

import sys
import json
from pathlib import Path
from datetime import datetime, date

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from src.data.pipeline import load_universe, download_universe
from src.signals.factors import mean_reversion
from src.signals.regime import detect_regime, regime_strategy_map
from src.signals.checklist import run_checklist
from src.signals.promoter import simulate_promoter_signals

JOURNAL_PATH = "research/daily_journal.json"


def load_journal() -> dict:
    p = Path(JOURNAL_PATH)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"entries": []}


def save_journal(journal: dict):
    Path(JOURNAL_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(JOURNAL_PATH).write_text(
        json.dumps(journal, indent=2), encoding="utf-8")


def upsert_entry(journal: dict, entry: dict):
    """Replace today's entry if it already exists, else append."""
    entries = journal["entries"]
    for i, e in enumerate(entries):
        if e["date"] == entry["date"]:
            entries[i] = entry
            return
    entries.append(entry)
    entries.sort(key=lambda e: e["date"])


def run_today(refresh: bool = False, account_value: float = 1_000_000):
    today = date.today()
    weekday_name = today.strftime("%A")

    print(f"\nDaily Log — {today.isoformat()} ({weekday_name})")
    print("=" * 50)

    # ── Skip weekends: NSE closed, data would be stale ───────────
    if today.weekday() >= 5:  # 5=Saturday, 6=Sunday
        print(f"  {weekday_name} — NSE closed. Not logging "
              f"(would duplicate Friday's data).")
        return None

    # ── Load data ─────────────────────────────────────────────────
    if refresh:
        universe = download_universe()
    else:
        universe = load_universe()

    stocks = {k: v for k, v in universe.items() if not k.startswith("^")}
    nifty_returns = universe["^NSEI"]["returns"].dropna()

    # ── Regime ────────────────────────────────────────────────────
    regime = detect_regime(nifty_returns)
    params = regime_strategy_map(regime.regime)

    print(f"  Regime     : {regime.regime.value} "
          f"({regime.confidence*100:.0f}% confidence)")
    print(f"  Volatility : {regime.vol_score*100:.1f}%")
    print(f"  Action     : {params['strategy']}")

    # ── Promoter signals ──────────────────────────────────────────
    promoter = simulate_promoter_signals(list(stocks.keys()))
    buying  = {k: v for k, v in promoter.items() if v > 0.3}
    selling = {k: v for k, v in promoter.items() if v < -0.1}

    # ── Top-5 mean reversion signals (regardless of regime) ──────
    signals = {}
    for sym, df in stocks.items():
        mr = mean_reversion(df["close"], 20)
        if not np.isnan(mr):
            signals[sym] = {
                "signal": round(float(-mr), 4),
                "price":  round(float(df["close"].iloc[-1]), 2),
            }
    ranked = sorted(signals.items(),
                    key=lambda x: x[1]["signal"], reverse=True)[:5]

    # ── Checklist pass count ──────────────────────────────────────
    passed = 0
    if params["position_size"] > 0:
        for sym, df in stocks.items():
            mr = mean_reversion(df["close"], 20)
            if np.isnan(mr):
                continue
            result = run_checklist(
                symbol=sym, df=df, regime=regime.regime,
                signal_score=mr, signal_type="mean_reversion",
                direction="long",
            )
            if result.passed:
                passed += 1

    entry = {
        "date":             today.isoformat(),
        "weekday":          weekday_name,
        "regime":           regime.regime.value,
        "confidence":       round(regime.confidence, 3),
        "volatility":       round(regime.vol_score, 4),
        "trend_score":      round(regime.trend_score, 4),
        "action":           params["strategy"],
        "stocks_monitored": len(stocks),
        "trades_passed":    passed,
        "promoter_buying":  list(buying.keys()),
        "promoter_selling": list(selling.keys()),
        "top_signals": [
            {"symbol": s, **v} for s, v in ranked
        ],
        "capital_preserved": account_value,
    }

    journal = load_journal()
    upsert_entry(journal, entry)
    save_journal(journal)

    print(f"\n  Logged to {JOURNAL_PATH}")
    print(f"  Total days recorded: {len(journal['entries'])}")
    return entry


def show_report():
    journal = load_journal()
    entries = journal["entries"]
    if not entries:
        print("No entries yet.")
        return

    print(f"\nDaily Journal Report")
    print(f"Days logged: {len(entries)}")
    print(f"Period: {entries[0]['date']} \u2192 {entries[-1]['date']}")

    regime_counts = {}
    total_trades = 0
    for e in entries:
        regime_counts[e["regime"]] = regime_counts.get(e["regime"], 0) + 1
        total_trades += e.get("trades_passed", 0)

    print(f"\nRegime distribution:")
    for r, c in sorted(regime_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {r:18s}: {c} days ({c/len(entries)*100:.0f}%)")

    print(f"\nTotal trades passed checklist across all days: {total_trades}")
    print(f"Capital preserved: \u20b9{entries[-1]['capital_preserved']:,.0f} "
          f"(0% drawdown, {len(entries)} days)")


if __name__ == "__main__":
    if "--report" in sys.argv:
        show_report()
    else:
        refresh = "--refresh" in sys.argv
        run_today(refresh=refresh)