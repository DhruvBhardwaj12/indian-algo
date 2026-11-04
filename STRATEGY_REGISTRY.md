# STRATEGY REGISTRY (11 Sep - 29 Oct 2026)

Built from the DeepSeek chat export. Paper trading only. No real money has been traded.

## READ THIS FIRST: how far to trust this file
- Built from ALL of the user's messages plus about 45 key result/verdict messages (of ~350 AI replies). It is NOT a line-by-line reading.
- Every number was copied from DeepSeek's own output in the chat. None were re-run. Check them against the real scripts and logs before relying on them.
- UNSURE = the chat did not make this clear. Do not guess; check the code.
- Status words: REJECTED, PASSED-HISTORICAL (passed old data, failed or untested on recent data), PAPER-TRADING (running or was running), UNVALIDATED (claimed good, evidence weak), DIAGNOSTIC (a measurement, not a strategy).
- Evidence grade: A = survived out-of-sample AND recent data. B = historical walk-forward only. C = tiny sample (under 30 trades/events) or modeled option prices. D = known bug or contradicted.

## Index

| ID | Name | Market | Status | Grade | One-line reason |
|---|---|---|---|---|---|
| EXP-001 | MA crossover 1H | Crypto spot | REJECTED | - | Cost drag 84% (67 trades x 1.25%) |
| EXP-002 | MA crossover 1D | Crypto spot | REJECTED | - | Walk-forward -24.46% |
| EXP-003 / LAB-012/013 | Funding carry (3 tries) | Crypto | REJECTED | D | Sharpe 12 was a bug; fixed version loses |
| EXP-004 | Donchian + RSI, multi-timeframe | Crypto futures | PASSED-HISTORICAL | B | Failed recent period; trader switched off |
| LAB-001 | TSMOM (4H) | Crypto futures | PAPER-TRADING (ETH mainly) | B/A- | Only crypto strategy still positive recently; BTC failed |
| LAB-002 | RSI(2) 5m | Crypto | REJECTED (kept as "museum") | - | -99.97%, cost drag 480%/yr |
| LAB-003B | Bollinger 1m | Crypto | REJECTED | - | -87% in 3 months |
| LAB-003C | Hour-of-day | Crypto | REJECTED | - | No hour passes Bonferroni |
| LAB-004 | RSI(2) 5m, 8 symbols | Crypto | REJECTED | - | All 8 lost 75-90% in 6 months |
| LAB-005 | SPY -> BTC cross-asset | Crypto | REJECTED | - | Correlation +0.01 |
| LAB-006 | Frequency map | Crypto | DIAGNOSTIC | - | Net edge vanishes below ~1-4H |
| LAB-007 | Cross-sectional momentum | Crypto futures | PASSED-HISTORICAL | B | Sharpe 1.67 historical, +0.08 recent |
| (unindexed) | Filtered CS momentum (long-only, top 3) | Crypto | REJECTED | B | Failed when window extended to 2024 |
| LAB-009/010 | CS reversion + pair spread | Crypto | REJECTED | B | Walk-forward -5.1%; dies at 15 bps |
| LAB-011 | Leveraged trend rider | Crypto | REJECTED | D | Impossible Sharpe; 3x/5x wiped out |
| LAB-014 | Vol-targeting overlay | Crypto | REJECTED | - | Hurts TSMOM |
| LAB-015 | Funding z-score contrarian | Crypto | REJECTED | - | Recent portfolio Sharpe -0.07 |
| (unindexed) | Deribit VRP (short vol) | Crypto options | REJECTED | - | Sharpe +0.01; premium real but signal picks bad days |
| (unindexed) | Regime switching | Crypto | REJECTED | - | Worse than always-on TSMOM |
| LAB-016/017 | Signal scan, market diagnostic | Crypto | DIAGNOSTIC | - | Old edges decayed; regime shifted |
| IND-001 | Opening range breakout, 10 stocks | India equity | REJECTED | - | PF 0.70, -62.7% in 60 days |
| IND-002 | Trap & squeeze, midcaps, 5x | India equity | REJECTED | - | PF 0.70, -124% |
| IND-003 | Nifty/BankNifty stat arb | India index | REJECTED | - | Costs exceed edge; steamroller losses |
| IND-004 | Event IV-crush iron condor (RBI, Budget, FOMC, US CPI) | Nifty options | UNVALIDATED | C | 10-13 events per variant; end-of-day prices |
| IND-005 | VIX + PCR sentiment (Nifty calls/puts) | Nifty options | UNVALIDATED | C | 11 trades total, only 4 calls |
| IND-006 | Multi-symbol "Panic Bounce" (RSI-2 under 10) | India stock options | UNVALIDATED | D | Option P&L is a formula, profit rose when costs were added |

## Validation toolkit used (keep using it)
- Parameter sweep (the full grid is logged, not just the best). A sweep alone proves nothing; DeepSeek flagged this itself (Sep 22).
- Walk-forward (train on a window, test on the next unseen one). This killed EXP-002.
- Year/regime breakdown; bootstrap Sharpe (5th percentile must be above 0); trade sign test; Bonferroni when many hypotheses are tested.
- Recency test: historical = 2020-2025, recent = 2025-01 to 2026-09. Passing only the old window is a fail.
- Cost sensitivity at 5, 10, 15, 25 bps per side. Many strategies die at 15 bps.
- Rule: any Sharpe above ~3 means a bug until proven otherwise (Sharpe 12, 13 and 13.04 were all bugs/artifacts).

## Cost assumptions (check which one each script actually uses)
- Crypto spot, India: 1.25% round trip (1% TDS + fees), 12.5 bps buy / 112.5 bps sell (Sep 11).
- Crypto futures: 5 bps per side base (10 bps round trip), tested up to 25.
- India intraday equity: DeepSeek calculated about 14 bps round trip (~Rs 140 per Rs 1 lakh) and said to use 15 bps (Oct 28). Earlier index stat-arb runs used 7 bps and 3.5 bps per side: too low.
- India options: 1% slippage on premium assumed in the Panic Bounce model. UNSURE what the IV-crush batch uses.

---

## A. CRYPTO (11 Sep - 2 Oct)

Setup: Binance data via ccxt/own fetcher, 2020-2025 historical plus recent 2025-01 to 2026-09. Paper equity $120 (about Rs 10,000) for TSMOM/Donchian; $1,000 for the 5m "museum".

### EXP-001 MA crossover 1H (REJECTED)
2023 data. BTC -21.07%, ETH -36.89% vs buy-and-hold +157% / +92%. 67 / 60 trades, Sharpe -0.50 / -1.11, win rate 22-25%. 67 trades x 1.25% = 84% cost drag. Lesson: trade frequency matters most for Indian spot crypto.

### EXP-002 MA crossover 1D (REJECTED)
5 years: BTC +849% (Sharpe 1.25), ETH +659% (0.96), only 8 trades each. Sweep: 47/47 pairs Sharpe above 0.5. But walk-forward -24.46% compounded, mean test Sharpe -0.09; trade sign test p = 1.000. It was a "long-biased in a bull market" illusion.

### EXP-003 + LAB-012/013 Funding carry (REJECTED, 3 attempts)
v1 showed Sharpe 12.3 / 13.9 = bug (basis risk ignored). Fixed version (Sep 23): BTC historical -8.35% (Sharpe -5.94), recent -9.52%; ETH -8.05% / -9.30%. Funding income was positive but basis P&L swamped it (e.g. BTC historical income +$657 vs basis -$1,174). A first file-naming bug also existed. User found it "getting complex". Closed.

### EXP-004 Donchian + RSI, 1H/4H multi-timeframe (PASSED-HISTORICAL, now OFF)
- Rules: UNSURE of exact entry/exit text. BTC walk-forward picked parameters (40, 30, 55) in all 4 windows (meaning of each number: check the script). 4H RSI filter on 1H Donchian breakout, long-only futures.
- Historical: Sharpe 0.67 / 0.76 (BTC / ETH), 250 / 251 trades, max DD -51% / -52%, PF 1.26 / 1.20. Sweep 27/27 positive. Walk-forward +194.5% / +94.5%, 3 of 4 windows profitable. Bootstrap P(Sharpe>0) 93-95%.
- Recent (2025-01 to 2026-09): Sharpe -0.53 BTC / -0.25 ETH at 5 bps. FAILED at every cost level.
- Paper trader: started 23 Sep, crashed that day (refactor bugs), "dead" by 30 Sep. Do not restart.
- Files: scripts/paper_trade_donchian_rsi.py, config/paper_trading.yaml.

### LAB-001 TSMOM, 4H (PAPER-TRADING, the best survivor)
- Rule: time-series momentum on 4H bars; default lookback 42; BTC walk-forward preferred 168 in all windows (slow); long/flat. UNSURE of full entry/exit and position sizing.
- Historical: Sharpe 0.88 BTC / 1.21 ETH, ~376 / 369 trades (75/yr), BTC max DD -75.5%. Walk-forward +385.9% BTC / +153.3% ETH, 3/4 windows each; bootstrap 5th percentile +0.09 / +0.44.
- Correlation with Donchian +0.59 / +0.61. Combining lowered Sharpe (BTC 1.51 to 1.28) but cut max DD (-42.5% to -32.7%).
- Recent OOS at 5 / 10 / 15 bps: BTC Sharpe -0.27 / -0.47 / -0.67 (FAIL). ETH Sharpe +0.61 / +0.49 / +0.37, CAGR +33.7% / +22.5% / +12.5% (HOLDS).
- Paper trading from 23 Sep: after 6 days TSMOM ETH $119.99 and BTC $119.99 (-0.01%), zero trades closed. The risk engine capped positions at 20% of equity. The traders repeatedly stopped without anyone noticing (window closed); see PROJECT_CONTEXT.
- Verdict: "ETH only, cost-sensitive, no real closed-trade evidence yet." Evidence is thin despite the strong backtest.
- Files: scripts/paper_trade_tsmom_eth.py, scripts/paper_trade_tsmom.py, scripts/validate_tsmom.py, config/paper_trading_tsmom*.yaml.

### LAB-002 RSI(2) 5m, "museum" (REJECTED; kept running as a teaching exhibit)
Net -99.97%, cost drag ~480%/yr, ~13 trades/day. Paper equity $1,000; 6 trades, $996.19 after 6 days. The risk engine cut 18 oversized signals to 20%. File: scripts/paper_trade_rsi2_5m.py.

### LAB-003B / 003C / 004 / 005 / 006
- 003B 1m Bollinger: -87% / -89% in 3 months; win rate 56-59% but PF 0.57-0.60.
- 003C hour-of-day: 0 of 48 tests pass Bonferroni (t above 3.1).
- 004 8-symbol RSI(2) 5m: all lost 75-90% in 6 months; PF 0.71-0.91.
- 005 SPY->BTC: correlation +0.0102 (t = 0.56); backtest -18.25%, Sharpe -0.60, PF 1.02.
- 006 frequency map (BTC, 2024-07 to 2025-01): net Sharpe 4H 1.74, 1H 0.81, 15M 0.25, 5M -0.27, 1M -2.15. ETH: 4H 0.80, 1H -0.09. Conclusion: net edge disappears below ~1-4H for a retail cost base.

### LAB-007 Cross-sectional momentum (PASSED-HISTORICAL, FAILED RECENT)
Rank coins by momentum and hold the leaders (long-only, top-3 in the later version). 81-config sweep: 79 positive, median Sharpe 1.41; chosen 42/3/3/6 = Sharpe 1.669; walk-forward chose 84/3/2/6 every time: 4/4 windows, +1287.7%, mean test Sharpe 1.775. Recent OOS Sharpe +0.08. DeepSeek called it "the strongest validation result" then "dead in the recent period". Not deployed.
Filtered long-only top-3 variant (daily ranking + trend filter): had a bug first (impossible numbers, fixed). Recent window: 4/4 rolling windows and 5/5 quarters positive, bootstrap 5th percentile -0.044. Extended back to 2024-01: +40.1% vs BTC buy-and-hold +104.5%, Sharpe 0.57 vs 0.80, one quarter of -31.82%. REJECTED.

### LAB-009/010, 011, 014, 015, VRP, regime switching (all REJECTED)
- Candidate D (CS reversion): 162-config sweep median Sharpe 0.11; dies at 15 bps. Candidate A (BTC/ETH spread): negative on every historical config, positive on recent configs (Sharpe +0.79 at 5 bps) but dead at 15 bps. 50/50 combo looked good in-sample (Sharpe 1.09, corr 0.10) but walk-forward -5.10%, 1 of 2 windows.
- LAB-011 leveraged trend rider: historical Sharpe 13.04 (artifact); 3x/5x = -100%; recent negative at all leverage.
- LAB-014 vol-targeting: hurt TSMOM. LAB-015 funding z-score (19 symbols): historical Sharpe +0.73, recent -0.07.
- VRP (Deribit DVOL): BTC mean premium +4.73%, t = +10.73 over 940 days (real); ETH -0.13% (none). Threshold-based short-vol strategy returned Sharpe +0.01 because it fires on the worst days. A constant-harvest version was suggested but NOT built (tail risk).
- Regime switching: classifier works, but switching ~50 times/year costs more; BTC Sharpe 0.04 vs always-on TSMOM 0.92.

### LAB-016/017 Diagnostics (30 Sep)
Taker-flow signal historically t = -8.58, recent +0.83 (gone). Funding z-score kept its direction but weakened (t -3.85 to -2.13). vol_ratio at 24h flipped sign (t +7.67 to -8.69): the one untested lead. Return autocorrelation at 4H flipped; dispersion down 30%.

---

## B. INDIA (2 Oct - 29 Oct): new folder indian-algo, capital Rs 20,000 (later asked about 50,000)

### IND-001 Opening range breakout (REJECTED, 2 Oct)
10 large NSE stocks, 60 days: 518 trades, win 39.6%, PF 0.70, -Rs 12,544 (-62.7%). 9 of 10 symbols lost; 54% of exits were end-of-day.

### IND-002 Trap & squeeze (REJECTED, 28 Oct)
SUZLON, YESBANK, PAYTM, BEL, IDEA, ADANIENT at 5x leverage: PF 0.70, -124% of Rs 20k. Only BEL was positive (PF 1.38). DeepSeek admitted its premise was wrong.

### IND-003 Nifty/BankNifty stat arb (REJECTED, 28 Oct)
First run: average reversion profit ~Rs 30 vs cost ~Rs 70 per trade. Second run (ADX filter, Z-stop 3.0): 13 trades, win rate 69.2%, PF 0.76, -Rs 135; avg win ~+Rs 410, avg loss ~-Rs 1,200.

### IND-004 Event IV-crush iron condor (UNVALIDATED, Grade C)
- Idea: sell Nifty ATM straddle / buy 500-point wings the day before an event (T-1 close), buy back after the event. Source of "edge": volatility risk premium / IV drop after the event.
- Data: NSE bhavcopy END-OF-DAY option closes for T-1 and T (script scripts/fetch_bhavcopy.py, scripts/backtest_iv_crush_batch.py). Real intraday fills not tested. Lot size 50 assumed.
- Results as stated by DeepSeek: RBI + Budget, 10 events: win 60%, +Rs 7,069, PF 2.69, best +5,047, worst -3,099. With FOMC added (13 events): win 53.8%, +Rs 5,469. CONFLICT: PF for this same set is stated as 1.76 in one message and 4.08 in the next. Naked straddle same events: +Rs 11,667, worst -Rs 7,439 (37% of Rs 20k). US CPI only (10-12 events/yr): win 83.3%, +Rs 8,004, PF 2.57, worst -Rs 6,315 (Sep 2024 gap).
- Problems: 10-13 events is far too few to call an edge ("Holy Grail" and "VALIDATED" were DeepSeek's words); FOMC has overnight gap risk; margin for a Nifty iron condor is ~Rs 1-1.25 lakh vs a Rs 20k account; no walk-forward, no cost sweep known.
- Routine: manual. Next event US CPI on 10-11 Nov 2026: run scripts/option_tracker.py at 3:00 PM IST on T-1 and 9:30 AM on T, log in research/paper_trading/iv_crush_log.md. Strategy card: research/strategy_cards/monthly_cpi_crush.md (created per chat; check it exists).

### IND-005 VIX + PCR sentiment (UNVALIDATED, Grade C)
Rule: VIX above ~18 and PCR below 0.85 = buy Nifty calls ("panic bounce"); VIX below ~12 with high PCR = buy puts. Results: 11 trades, +Rs 6,034; calls 4 trades 75% win +Rs 3,475; puts 7 trades 42.9% win +Rs 2,560 (profit came mostly from one 29 Sep crash day, +Rs 2,820). DeepSeek first proposed dropping puts, then agreed to keep both. n=4 is not evidence.

### IND-006 Multi-symbol Panic Bounce (UNVALIDATED, Grade D)
- Rules (frozen per chat): 10 liquid stocks (Reliance, HDFC Bank, ICICI Bank, Infosys, TCS, Bharti Airtel, SBI, L&T, ITC, Kotak); price above 50-day SMA; RSI-2 below 10 = buy ATM call; exit when RSI above 60 (the paper trader assumes +40% option gain on exit: a placeholder). Auto trader scans 7 assets at 3:15 PM IST.
- Backtest: 69 trades / 2 years, win 65.2%, +Rs 12,195, then loss cap added (+Rs 34,862), then "realistic" model (+Rs 51,918, win 59.4%).
- RED FLAGS: (1) option P&L is a formula: 4x the stock move, then a 1.5x "gamma boost", loss capped at premium (Rs 1,000). No real option prices used. (2) Profit went UP when slippage/theta were added: a sign the model is wrong, not that the strategy is better. (3) DeepSeek itself later said the setup is "about 80% realistic" and the 4x multiplier is "the biggest lie". (4) Lot sizes make Rs 1,000 risk unrealistic: 1 Reliance lot at a Rs 20 premium costs Rs 10,000. (5) yfinance daily data, not live. Treat all P&L figures as meaningless until real option premiums are used.
- Live paper status (29 Oct 05:25): scripts/auto_paper_trader_multi.py started; dashboard shows all zeros; market closed; no trade yet. Plan: Dhan sandbox (needs static IP whitelisting, ~1 day) and real option premiums.

---

## C. Cross-cutting findings
1. Retail costs kill anything faster than ~1-4H. 5m and 1m strategies lose 75-100% even with 55-62% win rates.
2. Strategies that pass old data but fail 2025-26 are common: EXP-004, LAB-007, filtered momentum.
3. In-sample sweeps and Sharpe above ~3 are misleading; walk-forward and recent-window tests decide.
4. The only Indian "wins" so far come from tiny samples or modeled option prices. None has survived a test comparable to the crypto ones (walk-forward + recent window + cost sweep).
5. DeepSeek's tone swung from careful (Sep) to hyped ("holy grail", "massive win", "fully automated trading desk") in late Oct. Judge by the evidence grade above, not the wording.

## D. Open items to verify against code (UNSURE)
- Exact rules and parameter meanings for EXP-004 and TSMOM; position sizing and stops.
- Which capital figure the Indian scripts use (Rs 20,000, Rs 50,000, or the Rs 2,00,000 virtual base in the Dhan sandbox script).
- Which cost model each Indian script uses.
- Whether the crypto TSMOM traders are still running (last confirmed 30 Sep) and whether research/lab/INDEX.md and strategy cards exist on disk.
- Whether scripts\status_indian.py exists on disk (the final chat message tells the user to run it).
