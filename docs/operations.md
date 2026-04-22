# Operations

## Backtest

Run:

```bash
python scripts/run_backtest.py --config config/strategy.yaml --data data/sample/ohlcv.csv --out outputs/example
```

Review:

- `metrics.json` for performance summary.
- `orders.csv` and `fills.csv` for order audit.
- `run.log.jsonl` for operational event logs.
- `config_snapshot.yaml` for reproducibility.

## Paper

Run:

```bash
python scripts/run_paper.py
```

Paper execution uses the same order model as backtests and can be extended with a scheduled data loop.

## Live Checklist

- Keep `broker.yaml` in `dry_run: true` until credentials, account mapping, and order routing are verified.
- Set `KIS_ACCOUNT_ID`, `KIS_APP_KEY`, `KIS_APP_SECRET`, and `KIS_ACCESS_TOKEN`.
- Reconcile local state with broker state before sending new orders.
- Enter safe mode if positions, cash, or open orders disagree.

## Recovery

1. Load local state from `StateStore`.
2. Pull broker account, positions, and open orders.
3. Compare local and broker state.
4. If mismatched, block new orders and inspect logs.
5. Resume only after state is reconciled.

