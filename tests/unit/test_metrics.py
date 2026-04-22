from __future__ import annotations

import pandas as pd
import pytest

from quent.analytics.metrics import calculate_drawdown, calculate_metrics, max_drawdown_duration


def test_drawdown_and_duration() -> None:
    # 110에서 105로 내려간 구간 하나가 최대 드로다운이다.
    equity = pd.Series([100.0, 110.0, 105.0, 120.0])

    drawdown = calculate_drawdown(equity)

    assert round(float(drawdown.min()), 6) == round(105 / 110 - 1, 6)
    assert max_drawdown_duration(drawdown) == 1


def test_metrics_include_trade_and_exposure_fields() -> None:
    # 작은 synthetic 결과로 지표 dict에 거래/노출/벤치마크 값이 들어오는지 검증한다.
    equity_curve = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=4),
            "equity": [100.0, 110.0, 105.0, 120.0],
            "exposure": [0.0, 0.5, 0.5, 0.5],
        }
    )
    cash = pd.DataFrame({"date": equity_curve["date"], "cash_weight": [1.0, 0.5, 0.5, 0.5]})
    fills = pd.DataFrame({"notional": [50.0, 55.0]})
    trades = pd.DataFrame({"pnl": [5.0]})
    market_data = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=4),
            "ticker": ["AAA"] * 4,
            "close": [10.0, 11.0, 11.5, 12.0],
        }
    )

    metrics = calculate_metrics(equity_curve, cash, fills, trades, market_data, 100.0, "AAA")

    assert metrics["final_equity"] == 120.0
    assert metrics["trade_count"] == 1
    assert metrics["buy_hold_return"] == pytest.approx(0.2)
