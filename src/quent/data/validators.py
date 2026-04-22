"""OHLCV 입력 데이터가 전략에 안전한 형태인지 검증하는 모듈."""

from __future__ import annotations

import pandas as pd

from quent.core.constants import REQUIRED_OHLCV_COLUMNS
from quent.core.exceptions import DataValidationError


class OhlcvValidator:
    """일봉 long-format OHLCV 데이터의 품질 규칙을 검사한다."""

    def validate(self, frame: pd.DataFrame) -> pd.DataFrame:
        """컬럼, 날짜, 중복, 결측, 가격 논리를 검증하고 정렬된 DataFrame을 반환한다."""

        # 필수 컬럼이 없으면 이후 계산이 조용히 틀어질 수 있으므로 즉시 실패한다.
        missing = [col for col in REQUIRED_OHLCV_COLUMNS if col not in frame.columns]
        if missing:
            raise DataValidationError(f"Missing required columns: {missing}")
        if frame.empty:
            raise DataValidationError("Market data is empty.")

        # 원본 DataFrame을 보존하기 위해 복사본에서 정규화한다.
        data = frame.copy()
        # 날짜는 pandas datetime으로 변환하고 일봉 기준으로 normalize한다.
        data["date"] = pd.to_datetime(data["date"], errors="raise")
        if getattr(data["date"].dt, "tz", None) is not None:
            data["date"] = data["date"].dt.tz_convert(None)
        data["date"] = data["date"].dt.normalize()

        # 같은 종목의 같은 날짜 bar가 두 개 있으면 체결/평가가 모호해진다.
        duplicate_mask = data.duplicated(["date", "ticker"], keep=False)
        if duplicate_mask.any():
            duplicates = data.loc[duplicate_mask, ["date", "ticker"]].head().to_dict("records")
            raise DataValidationError(f"Duplicate date/ticker rows found: {duplicates}")

        # 핵심 OHLCV 컬럼의 결측은 신호와 포트폴리오 평가를 오염시킨다.
        if data[["open", "high", "low", "close", "volume"]].isna().any().any():
            raise DataValidationError("OHLCV columns cannot contain missing values.")

        # 가격은 양수, 거래량은 0 이상이어야 한다.
        price_columns = ["open", "high", "low", "close"]
        if (data[price_columns] <= 0).any().any():
            raise DataValidationError("Prices must be positive.")
        if (data["volume"] < 0).any():
            raise DataValidationError("Volume cannot be negative.")
        # high/low가 open/close를 감싸지 못하면 잘못된 bar다.
        if (data["high"] < data[["open", "close", "low"]].max(axis=1)).any():
            raise DataValidationError("High must be >= open, close, and low.")
        if (data["low"] > data[["open", "close", "high"]].min(axis=1)).any():
            raise DataValidationError("Low must be <= open, close, and high.")

        # 종목별 시계열 연산을 안정적으로 하기 위해 ticker/date 순서로 정렬한다.
        sorted_data = data.sort_values(["ticker", "date"]).reset_index(drop=True)
        for ticker, group in sorted_data.groupby("ticker", sort=False):
            if not group["date"].is_monotonic_increasing:
                raise DataValidationError(f"Dates are not sorted for ticker {ticker}.")
        return sorted_data
