from __future__ import annotations

import math

import pandas as pd

from quent.indicators.moving_average import ema, sma


def test_sma_matches_manual_values() -> None:
    # window=3이면 앞의 두 값은 warm-up NaN이고 이후 평균은 2, 3, 4다.
    values = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])

    result = sma(values, 3)

    assert math.isnan(result.iloc[0])
    assert math.isnan(result.iloc[1])
    assert result.iloc[2:].tolist() == [2.0, 3.0, 4.0]


def test_ema_uses_adjust_false_and_warmup_nan() -> None:
    # adjust=False EMA의 수작업 기대값을 고정해 공식 변경을 감지한다.
    values = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])

    result = ema(values, 3)

    assert math.isnan(result.iloc[0])
    assert math.isnan(result.iloc[1])
    assert result.iloc[2] == 2.25
    assert result.iloc[3] == 3.125
    assert result.iloc[4] == 4.0625
