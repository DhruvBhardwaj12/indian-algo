# Indian Market Strategy Registry

This document tracks every strategy tested in the Indian market, along with its verdict and the data used.

## 🏆 VALIDATED STRATEGIES (Ready for Paper Trading)

### 1. Event-Driven IV Crush (Iron Condor)
*   **Logic:** Sell ATM Straddle, Buy 500pt OTM Wings, 1 day before US CPI / RBI Policy. Exit the next morning.
*   **Data:** Real historical NSE Bhavcopy settlement prices.
*   **Backtest Results:** 13 events, 53.8% Win Rate, **Profit Factor 1.76**, +₹5,469 P&L (1 lot).
*   **Status:** **VALIDATED.** Executing manually on Nov 9/10.

### 2. Panic Bounce (IND-006)
*   **Logic:** Scan 15 heavyweights daily at 3:15 PM. Buy ATM Call if RSI(2) < 10 and Price > 50 SMA.
*   **Data:** yfinance daily data (simulated Greeks for backtest).
*   **Backtest Results:** 116 trades, 62.1% Win Rate, +₹94,659 P&L (fantasy options math).
*   **Status:** **RUNNING LIVE IN PAPER.** Currently using real live NSE option prices via `indiaopt`.

### 3. VIX + PCR Confluence (Macro Filter)
*   **Logic:** Buy Calls only when India VIX > 18 and Nifty PCR < 0.85.
*   **Data:** yfinance (VIX) + NSE Bhavcopy (PCR).
*   **Backtest Results:** 75% Win Rate on Calls.
*   **Status:** **VALIDATED FOR RESEARCH.** Not automated yet.

---

## 🧪 UPGRADES TESTED (Rejected)

*   **Macro Kill Switch (Nifty > 200 SMA + VIX < 25):** Failed. Filtered out the biggest winners. P&L dropped from ₹94k to ₹7k.
*   **OTM Options:** Failed. Relled on fake leverage multipliers.
*   **Trailing Stop (Premium +30%):** Failed. Never triggered because the RSI > 60 exit fires first.
*   **Intraday Confirmation (Wait for green candle):** Failed. Entered too late, Win Rate crashed from 62% to 33%.

---

## ☠️ FAILED STRATEGIES (Do Not Rebuild)

*   **Opening Range Breakout (ORB):** 17 bps cost drag killed it.
*   **Trap & Squeeze (High Beta Fade):** 5x leverage wiped out the account.
*   **Index Stat Arb (Nifty/BankNifty):** Spread reversion too small to cover costs.
*   **Overnight Anomaly:** 60-day sample too small, noise dominated.
*   **Dhan API Sandbox:** Hit endless `DH-906` and `DH-905` (static IP) errors. Abandoned.
*   **110% Realistic Options Buying (Theta/Vega):** Proved that buying Calls during a panic is a losing game (Win Rate dropped to 26%, P&L -₹20k).

---

## ⚙️ INFRASTRUCTURE RULES
1. **No Tuning:** We do not tweak RSI to 12 or 8 just to see if it works. We test structural upgrades only.
2. **Real Premiums:** We must use `indiaopt` for live prices, not fake multipliers.
3. **Costs:** 5 bps slippage assumed on all intraday equity trades.
