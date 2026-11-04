"""Indian Paper Trading Dashboard."""

import json
from pathlib import Path
from datetime import datetime

STATE_FILE = Path("research/paper_trading/multi_auto_state.json")

def main():
    if not STATE_FILE.exists():
        print("No trading data found yet. Run the auto-trader first.")
        return

    with open(STATE_FILE, "r") as f:
        state = json.load(f)

    equity = state.get("equity", 50000.0)
    initial = 50000.0
    open_pos = state.get("open_positions", [])
    closed = state.get("closed_trades", [])

    total_trades = len(closed)
    wins = sum(1 for t in closed if t["pnl"] > 0)
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl = sum(t["pnl"] for t in closed)
    return_pct = (equity / initial - 1) * 100

    print(f"\n{'=' * 60}")
    print(f"  INDIAN ALGO PAPER TRADING STATUS")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
    print(f"{'=' * 60}")
    print(f"  Current Equity:  ₹{equity:,.2f}")
    print(f"  Total P&L:       ₹{total_pnl:+,.2f} ({return_pct:+.2f}%)")
    print(f"  Total Trades:    {total_trades}")
    print(f"  Win Rate:        {win_rate:.1f}%")
    print(f"{'=' * 60}")

    print(f"\n  --- OPEN POSITIONS ({len(open_pos)}) ---")
    if not open_pos:
        print("  No open positions currently.")
    else:
        for p in open_pos:
            print(f"  {p['symbol']:<10} | {p['lots']} lot(s) | Entry: ₹{p['entry_price']:.2f} | Cost: ₹{p['cost']:,.2f}")

    print(f"\n  --- LAST 5 CLOSED TRADES ---")
    if not closed:
        print("  No closed trades yet.")
    else:
        for t in closed[-5:]:
            pnl_str = f"+₹{t['pnl']:,.2f}" if t['pnl'] > 0 else f"-₹{abs(t['pnl']):,.2f}"
            print(f"  {t['symbol']:<10} | {t['entry_date']} to {t['exit_date']} | P&L: {pnl_str}")
    print(f"\n{'=' * 60}\n")

if __name__ == "__main__":
    main()
    