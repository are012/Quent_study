"""SMA와 EMA 이동평균 지표를 계산하는 모듈."""

from __future__ import annotations

import pandas as pd


def _validate_window(window: int) -> None:
    """이동평균 window가 양수인지 확인한다."""

    if window <= 0:
        raise ValueError("window must be positive")


def sma(series: pd.Series, window: int) -> pd.Series:
    """window개 관측치가 모이기 전에는 NaN을 유지하는 단순 이동평균."""

    _validate_window(window)
    # min_periods=window로 warm-up 구간을 명시적으로 비워 둔다.
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    """window개 관측치가 모이기 전에는 NaN을 유지하는 지수 이동평균."""

    _validate_window(window)
    # adjust=False는 실시간 업데이트에 가까운 재귀형 EMA 계산이다.
    return series.ewm(span=window, adjust=False, min_periods=window).mean()
