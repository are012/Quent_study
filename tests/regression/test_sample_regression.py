from __future__ import annotations

import pytest

from quent.backtest.engine import BacktestEngine
from quent.config import load_config
from quent.data.loaders import CsvLongDataLoader


def test_sample_dataset_regression_metrics() -> None:
    # 고정 샘플 데이터의 핵심 결과값을 박아두어 의도치 않은 백테스트 변화가 보이게 한다.
    config = load_config("config/strategy.yaml")
    data = CsvLongDataLoader().load("data/sample/ohlcv.csv")

    result = BacktestEngine(config, run_id="regression").run(data)

    assert len(result.orders) == 1
    assert len(result.fills) == 1
    assert len(result.trades) == 0
    assert result.metrics["final_equity"] == pytest.approx(10_954_895.214775262)
    assert result.metrics["total_return"] == pytest.approx(0.0954895214775262)
