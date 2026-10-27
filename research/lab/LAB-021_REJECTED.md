# LAB-021 — Trap & Squeeze (High-Beta Fade)

## Hypothesis
High-beta stocks break out, trigger retail stops, then reverse.
Fade the failed breakout with 5x MIS leverage.

## Rules
- Opening range: first 15-min bar
- Long: break below OR low, reclaim within 3 bars
- Short: break above OR high, reject within 3 bars
- Target: opposite side of OR
- 5x leverage (₹1L notional on ₹20k capital)
- Cost: 7 bps round trip

## Results (60 days, 6 symbols)
- 267 trades, 39% win rate
- Profit factor: 0.70
- Net P&L: -₹24,828
- Return on ₹20k: -124%
- Gross P&L (no costs): -₹6,138 (strategy has negative edge)

## Verdict: REJECTED.

The "fade the fakeout" logic fails on high-beta stocks because
they trend hard on news. ADANIENT, PAYTM, IDEA all exhibited
multi-hour trends that stopped out the fade repeatedly.

BEL was the only winner (PF 1.38) — likely because PSU defense
stocks have different intraday microstructure. Not a generalizable
edge.

## Key learning
Fading breakouts requires a regime filter. Without it, you are
betting that every day is a choppy day, which is false for
high-beta names.
