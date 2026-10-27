# Strategy Card — Event-Driven IV Crush (Iron Condor)

## Hypothesis
Implied Volatility (IV) systematically inflates in the days leading up to scheduled macro events (RBI Policy, Union Budget, Fed). Retail traders overpay for options as insurance. When the event passes, the uncertainty vanishes, and IV collapses. We capture this premium by selling an Iron Condor the day before the event and buying it back the day after.

## Mechanism
Options are priced for maximum fear before a binary event. The actual realized move is almost always smaller than the implied move. By selling a defined-risk structure, we profit from the collapse in volatility (Vega) without exposing ourselves to unlimited directional risk (Gamma).

## Rules (Frozen)
- **Universe:** NIFTY 50 Index Options.
- **Setup (T-1):** Sell ATM Call, Sell ATM Put, Buy OTM Call (ATM+500), Buy OTM Put (ATM-500).
- **Exit (T):** Buy back ATM legs, Sell wings.
- **Holding Period:** 24-48 hours.
- **Expiry:** Must choose the expiry strictly *after* the event date.

## Backtest Results (10 events, 2024-2025)
- **Win Rate:** 60%
- **Profit Factor:** 2.69
- **Total Net P&L:** +₹7,069 (on 1 lot / ₹1.2L margin)
- **Worst Trade:** -₹3,099
- **Best Trade:** +₹5,047

## Real World Constraints
- **Margin:** Requires ~₹1.2L per lot. Cannot be traded on a ₹20k account.
- **Execution:** Must be executed at market open on T-1 and market open on T to avoid tail risk.

## Verdict
**VALIDATED for Paper Trading.** This is a real, structural edge in the Indian market. 
