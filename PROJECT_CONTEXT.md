# PROJECT CONTEXT (state as of 29 Oct 2026)

Read this first, then STRATEGY_REGISTRY.md. Built from a DeepSeek chat export (11 Sep - 29 Oct 2026); anything marked UNSURE must be checked in the real files.

## 1. Who and why
- A beginner in coding. Learning-first: wants to understand trading, with paper trading that is "100% realistic" (real costs, real prices, real fills), then possibly real money later. Explain things in plain language; define jargon.
- Capital reference: about Rs 10,000 (crypto era; paper equity $120), Rs 20,000 (Indian options era), asked about Rs 50,000. Goal: frequent trades and steady weekly/monthly gains, but the user accepts that evidence comes first.
- Markets: crypto (Binance, Deribit data) 11 Sep - 2 Oct; Indian market (NSE stocks/index/options) from 2 Oct, because crypto strategies stopped working recently.
- Broker: Dhan. Sandbox/API access blocked on a static-IP whitelisting step (about 1 day). Not connected as of 29 Oct.

## 2. Environment
- Windows, PowerShell, VS Code, Python 3.12, `uv` for running (`uv run python scripts\NAME.py`), git + GitHub (commit after each milestone).
- Note from the chat: `uv run` once hid an import error (missing numpy); running plain `python scripts\NAME.py` showed it.
- Two projects under `$HOME\Projects\`: `crypto-algo` and `indian-algo`. Always `cd` into the right one first (the chat had a "wrong folder" mistake).

## 3. Folder layout (from file names in the chat; confirm on disk)
```
crypto-algo/
  config/        settings.yaml, risk_limits.yaml, paper_trading*.yaml (tsmom, tsmom_eth, rsi2_5m)
  data/raw/      binance spot + futures parquet, funding, deribit/dvol
  docs/          decisions.md, review_2026-09-23.md
  research/lab/  INDEX.md (experiment log), TEMPLATE.md, dated experiment notes
  research/strategy_cards/   ma_crossover_daily_2020_2025.md, cs_momentum_filtered_recent.md, ...
  research/paper_trading/    *_state.json, *_log.jsonl (live paper traders write here)
  scripts/       fetch_*, validate_*, backtest_*, paper_trade_*, status.py, diagnostic.py, signal_scan.py
  src/crypto_algo/  data, features, backtesting, strategies, validation (sweep, walk_forward, bootstrap, regime), risk/engine.py, paper/ (runner, alt_runner, state, executor)
indian-algo/
  data/events.csv           event dates for the IV-crush study
  research/paper_trading/   iv_crush_log.md, multi_auto_state.json
  research/strategy_cards/  monthly_cpi_crush.md, multi_symbol_panic_bounce.md (created per chat; confirm)
  scripts/       fetch_nse_data.py, fetch_bhavcopy.py, backtest_*.py, option_tracker.py, live_scanner.py, auto_paper_trader_multi.py, status_indian.py
  src/indian_algo/  data/nse_fetcher.py, backtesting (pairs_simulator, intraday_simulator), strategies (orb, index_stat_arb)
```

## 4. Commands (all from the project folder, PowerShell)
Crypto:
- Status of all paper traders (run daily): `uv run python scripts\status.py`
- TSMOM ETH paper trader (leave window open): `uv run python scripts\paper_trade_tsmom_eth.py`
- TSMOM BTC (optional): `uv run python scripts\paper_trade_tsmom.py`
- 5m "museum" trader: `uv run python scripts\paper_trade_rsi2_5m.py`
- DO NOT RUN: `paper_trade_donchian_rsi.py` (failed recent test).
- Data refresh: `fetch_spot_recent.py`, `fetch_futures_data.py`, `fetch_dvol.py` (they read config\settings.yaml).
- Safety tests before changing anything: `test_risk_engine.py`, `test_features.py`, `validate_data.py`, `test_visibility.py`.
- Research: `diagnostic.py`, `signal_scan.py`, `validate_tsmom.py`.

India:
- Daily scanner/paper trader: `uv run python scripts\auto_paper_trader_multi.py` (sleeps until 3:15 PM IST, scans 7 assets; Task Scheduler setup was offered but not confirmed done).
- Event routine (manual): `uv run python scripts\option_tracker.py` on T-1 at 3:00 PM IST and T at 9:30 AM; log to research\paper_trading\iv_crush_log.md. Next event: US CPI, 10-11 Nov 2026.
- Dashboard: `uv run python scripts\status_indian.py` (UNSURE it exists; the chat wrote it at the end).
- Fetch data: `fetch_nse_data.py`, `fetch_bhavcopy.py YYYY-MM-DD`.

## 5. Current state (29 Oct 2026)
- Crypto: all validated strategies failed or weakened in 2025-26 except TSMOM on ETH (see registry). Last confirmed paper results on 30 Sep: portfolio -0.28%, essentially flat, TSMOM traders had zero closed trades. UNSURE whether any crypto trader is still running.
- India: three ideas marked "validated" in the chat are actually UNVALIDATED (tiny samples or modeled option prices). First live paper scan was blank (market closed). No trade has ever been placed in any account.
- Known recurring problems: traders silently stop when the PowerShell window closes; `status.py` flags this as STALE; the dashboard took many failed attempts because edits did not save (always check the file actually changed); YAML syntax errors are common; the user's PC must stay on for paper traders to run.

## 6. Method rules the user has accepted (keep enforcing)
1. Never tune on the test window. Hold out unseen data; walk-forward decides.
2. Test on the recent window (2025-01 to 2026-09) and at 15 bps per side before believing anything.
3. A Sharpe above ~3 is a bug until proven otherwise.
4. Log every experiment (win or lose) in research\lab\INDEX.md and write a strategy card with a frozen rule set.
5. Minimum bar to call something validated: walk-forward positive on 4+ windows, positive recent window, survives cost sensitivity, bootstrap 5th percentile Sharpe above 0, and at least 30 trades/events (options: real option prices, not multipliers).
6. Paper trading must model fees, slippage, lot sizes, and fill delays. Realism > profit.

## 7. Next steps (suggested, in order)
1. Verify the registry against the real scripts (parameters, costs, capital figures); fix mismatches in the registry by hand.
2. Re-check that nothing in IND-006 rests on the "4x multiplier"; replace with real option premiums (bhavcopy history or Dhan sandbox).
3. Expand the IV-crush sample (more events and years, including the bad ones) and test with cost sweeps; keep paper-logging the 10-11 Nov US CPI trade.
4. Decide whether to keep any crypto paper trader (TSMOM ETH only) and make a restart/watchdog routine.
5. Investigate the one untested crypto lead: `vol_ratio` at 24h (sign flipped, strongest recent t-stat).
6. Only after 3+ months of consistent paper results, discuss real money. This is education, not financial advice.
