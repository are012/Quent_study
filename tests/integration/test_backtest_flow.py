from __future__ import annotations

from pathlib import Path

from quent.backtest.engine import BacktestEngine
from quent.config import load_config
from quent.data.loaders import CsvLongDataLoader


def test_sample_backtest_writes_expected_artifacts(tmp_path: Path) -> None:
    # 샘플 CSV부터 백테스트 엔진, exporter까지 전체 경로를 한 번에 검증한다.
    config = load_config("config/strategy.yaml")
    data = CsvLongDataLoader().load("data/sample/ohlcv.csv")

    result = BacktestEngine(config, run_id="test_run").run(data, tmp_path)

    assert not result.equity_curve.empty
    assert len(result.orders) == 1
    assert len(result.fills) == 1
    assert result.metrics["final_equity"] > config.strategy.initial_capital
    # 운영/분석에 필요한 모든 산출물이 실제 파일로 쓰였는지 확인한다.
    for filename in [
        "equity_curve.csv",
        "cash.csv",
        "positions.csv",
        "orders.csv",
        "fills.csv",
        "trades.csv",
        "metrics.json",
        "config_snapshot.yaml",
        "tearsheet.png",
        "run.log.jsonl",
    ]:
        assert (tmp_path / filename).exists()
