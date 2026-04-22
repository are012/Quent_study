"""이동평균 교차 기반 raw/executable 신호를 생성하는 모듈."""

from __future__ import annotations

import pandas as pd

from quent.indicators.moving_average import ema, sma


class MovingAverageCrossoverSignalGenerator:
    """롱 온리 MA crossover 신호를 종목별로 계산한다."""

    def __init__(self, short_window: int, long_window: int, ma_type: str = "sma") -> None:
        # 잘못된 window는 look-ahead보다 먼저 전략 정의 자체를 깨뜨린다.
        if short_window <= 0 or long_window <= 0:
            raise ValueError("MA windows must be positive.")
        if short_window >= long_window:
            raise ValueError("short_window must be smaller than long_window.")
        if ma_type not in {"sma", "ema"}:
            raise ValueError("ma_type must be 'sma' or 'ema'.")
        self.short_window = short_window
        self.long_window = long_window
        self.ma_type = ma_type

    def generate(self, frame: pd.DataFrame, price_column: str = "signal_price") -> pd.DataFrame:
        """raw_signal과 하루 지연된 executable_signal을 포함한 DataFrame을 반환한다."""

        if price_column not in frame.columns:
            raise ValueError(f"Missing price column: {price_column}")
        # 설정에 따라 SMA 또는 EMA 함수를 선택한다.
        ma_func = sma if self.ma_type == "sma" else ema
        # 종목별 rolling 계산이 섞이지 않도록 ticker/date 순으로 정렬한다.
        data = frame.sort_values(["ticker", "date"]).copy()

        frames: list[pd.DataFrame] = []
        for _, group in data.groupby("ticker", sort=False):
            # 각 종목은 독립적인 시계열로 이동평균과 신호를 계산한다.
            prices = group[price_column].astype(float)
            group = group.copy()
            group["short_ma"] = ma_func(prices, self.short_window)
            group["long_ma"] = ma_func(prices, self.long_window)
            # warm-up이 끝난 구간에서만 raw signal을 유효하게 둔다.
            valid = group["short_ma"].notna() & group["long_ma"].notna()
            group["raw_signal"] = (group["short_ma"] > group["long_ma"]) & valid
            # 당일 종가로 만든 raw signal은 다음 거래 시점에만 실행 가능하다.
            previous_raw = group["raw_signal"].shift(1, fill_value=False).astype(bool)
            current_raw = group["raw_signal"].astype(bool)
            group["executable_signal"] = previous_raw
            # entry/exit는 분석용 이벤트 신호이며 주문은 executable_signal로 결정한다.
            group["entry_signal"] = current_raw & ~previous_raw
            group["exit_signal"] = ~current_raw & previous_raw
            frames.append(group)

        # 다시 날짜/ticker 순으로 정렬해 백테스트 엔진의 일별 처리에 맞춘다.
        return pd.concat(frames, ignore_index=True).sort_values(["date", "ticker"]).reset_index(drop=True)
