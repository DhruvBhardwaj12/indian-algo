# Strategy Card — Multi-Symbol Panic Bounce

## Hypothesis
Retail traders overreact to short-term negative news, dumping fundamentally strong stocks. By scanning a universe of highly liquid large-caps, we can identify when they are statistically oversold (RSI-2 < 10) but still in a long-term uptrend (Price > 50 SMA), and buy short-term Calls to capture the bounce.

## Rules (Frozen)
- **Universe:** Top 10 NSE Liquid Stocks (Reliance, HDFC, ICICI, Infosys, TCS, Bharti, SBI, L&T, ITC, Kotak).
- **Filter 1 (Macro):** Check India VIX (optional confluence).
- **Filter 2 (Trend):** Price > 50-day SMA.
- **Trigger:** 2-day RSI drops below 10.
- **Action:** Buy ATM Call.
- **Exit:** RSI-2 goes above 60, OR 4 days held.
- **Risk Management:** Allocate exactly 5% of equity per trade (₹1,000 premium paid). If the option goes to zero, max loss is ₹1,000.

## Backtest Results (2 Years)
- Total Trades: 69 (Roughly 3 trades per month)
- Win Rate: 65.2%
- Total P&L: +₹34,862
- Worst Trade: -₹1,000 (Capped risk)
- Max Drawdown: 5%

## Verdict
**VALIDATED.** This is our high-frequency engine. It provides constant weekly action, spreads risk across 10 different stocks, and has a strictly defined maximum loss.
