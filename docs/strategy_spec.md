# Strategy Specification

## Rules

- The strategy is long-only and switches between long and cash.
- `short_ma > long_ma` is the raw long regime.
- `short_ma <= long_ma` is the raw flat regime.
- Raw signals are calculated from the current daily close after that bar is complete.
- Executable signals are delayed by one trading row per ticker, so the default fill happens at the next trading day's open.
- If a long position already exists, repeated long signals do not add to the position.
- If the executable signal turns false, the whole long position is sold.

## Data Assumptions

- Input data is daily OHLCV in long CSV format: `date,ticker,open,high,low,close,volume`.
- Dates are normalized to timezone-naive daily dates.
- The default price column for indicators is `close`.
- `adjusted_close` can be enabled through config, and that choice must be recorded in output config snapshots.

## Costs And Fills

- Default fill model is `next_open`.
- Buy fill price is `open * (1 + slippage_bps / 10000)`.
- Sell fill price is `open * (1 - slippage_bps / 10000)`.
- Fees are proportional with an optional minimum fee.
- Tax is optional and applied only to sells.

## Risk Rules

- Default maximum position weight is 25%.
- Default maximum total exposure is 100%.
- Default maximum simultaneous positions is 4.
- Default maximum daily orders is 20.
- Cash shortages shrink buy orders; orders below minimum quantity or notional are rejected.

## Known Limits

- v1 excludes shorts, leverage, intraday bars, derivatives, machine learning, and complex optimizers.
- The KIS live adapter is a safe extension boundary and defaults to dry-run.

