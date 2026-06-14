"""
Paper Trading — tracks live signals without real money.
Run daily. After 30 days you have real validation data.

python scripts/paper_trade.py          # generate today's signals
python scripts/paper_trade.py --report # show P&L so far
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import numpy as np
import pandas as pd
from datetime import datetime, date

from src.data.pipeline import load_universe, download_universe
from src.signals.factors import mean_reversion
from src.signals.regime import detect_regime, regime_strategy_map


JOURNAL_PATH = "research/paper_trade_journal.json"


def load_journal() -> dict:
    p = Path(JOURNAL_PATH)
    if p.exists():
        return json.loads(p.read_text())
    return {"trades": [], "daily_log": []}


def save_journal(journal: dict):
    Path(JOURNAL_PATH).parent.mkdir(exist_ok=True)
    Path(JOURNAL_PATH).write_text(json.dumps(journal, indent=2))


def run_today(refresh: bool = False):
    today = date.today().isoformat()
    print(f"\nPaper Trading — {today}")
    print("=" * 50)

    if refresh:
        universe = download_universe()
    else:
        universe = load_universe()

    stocks = {k: v for k, v in universe.items()
              if not k.startswith("^")}

    # Regime
    nifty   = universe["^NSEI"]["returns"].dropna()
    regime  = detect_regime(nifty)
    params  = regime_strategy_map(regime.regime)

    # Signals
    signals = {}
    for sym, df in stocks.items():
        mr = mean_reversion(df["close"], 20)
        if not np.isnan(mr):
            price = float(df["close"].iloc[-1])
            signals[sym] = {
                "signal":  float(-mr),
                "price":   price,
                "rsi":     0.0,
            }

    # Top signals
    ranked = sorted(signals.items(),
                    key=lambda x: x[1]["signal"], reverse=True)

    journal = load_journal()

    day_log = {
        "date":    today,
        "regime":  regime.regime.value,
        "action":  params["strategy"],
        "signals": [],
        "trades":  [],
    }

    if params["position_size"] > 0:
        top5 = ranked[:5]
        for sym, s in top5:
            day_log["signals"].append({
                "symbol": sym,
                "signal": round(s["signal"], 4),
                "price":  s["price"],
            })
            print(f"  SIGNAL: {sym:20s} "
                  f"score={s['signal']:+.4f} "
                  f"₹{s['price']:,.0f}")
    else:
        print(f"  {regime.regime.value} — no trades")

    journal["daily_log"].append(day_log)
    save_journal(journal)
    print(f"\nLogged to {JOURNAL_PATH}")
    return day_log


def show_report():
    journal = load_journal()
    logs = journal["daily_log"]
    if not logs:
        print("No paper trading data yet. Run without --report first.")
        return

    print(f"\nPaper Trading Report")
    print(f"Days tracked: {len(logs)}")
    print(f"Period: {logs[0]['date']} → {logs[-1]['date']}")

    regime_counts = {}
    for log in logs:
        r = log["regime"]
        regime_counts[r] = regime_counts.get(r, 0) + 1

    print(f"\nRegime distribution:")
    for r, c in sorted(regime_counts.items(),
                       key=lambda x: x[1], reverse=True):
        print(f"  {r:20s}: {c} days ({c/len(logs)*100:.0f}%)")


if __name__ == "__main__":
    if "--report" in sys.argv:
        show_report()
    else:
        refresh = "--refresh" in sys.argv
        run_today(refresh=refresh)