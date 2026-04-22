# Assumptions

- Daily OHLCV bars are complete and ordered by exchange session.
- The next-open model assumes the order can be placed after the prior close and filled at the next listed open.
- Slippage is a simple fixed bps adjustment, not a volume-aware market-impact model.
- Fees and tax are deterministic config values.
- Partial fills, delayed fills, and no-fills are represented by interfaces but not simulated by default backtests.
- Benchmark comparison uses the configured ticker, or otherwise an equal average buy-and-hold return across input tickers.

