# Architecture

## Modules

- `data`: CSV loading, normalization, and OHLCV validation.
- `indicators`: SMA and EMA calculations.
- `signals`: MA crossover raw and executable signal generation.
- `portfolio`: cash, positions, sizing, and risk controls.
- `backtest`: daily event loop, fill simulator, and transaction costs.
- `analytics`: metrics and charts.
- `reporting`: CSV, JSON, YAML, PNG, and JSONL artifact export.
- `execution`: paper broker and KIS live adapter boundary.
- `storage`: JSON state store, trade log, and run registry.

## Data Flow

1. Load long-format CSV.
2. Validate dates, duplicates, missing values, price logic, and volume.
3. Add `signal_price`.
4. Generate short and long moving averages.
5. Generate raw signal from close and executable signal via one-row ticker-level delay.
6. Process each date sequentially: executable signal, order, fill, portfolio update, close mark.
7. Save run artifacts and metrics.

## Backtest Versus Live

- The backtest uses deterministic market bars and always fills accepted orders.
- Paper execution uses the same order and fill types but exposes broker-style order state transitions.
- Live execution is isolated behind `BrokerBase`; KIS credentials and transport are injected outside strategy logic.

