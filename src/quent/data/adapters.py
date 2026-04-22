"""검증된 시장 데이터를 전략 모듈이 쓰기 좋은 형태로 바꾸는 어댑터."""

from __future__ import annotations

import pandas as pd

from quent.core.exceptions import DataValidationError


class MarketDataAdapter:
    """가격 컬럼 선택과 정렬을 표준화한다."""

    def __init__(self, price_column: str = "close", use_adjusted: bool = False) -> None:
        # use_adjusted가 true면 price_column보다 adjusted_close를 우선한다.
        self.price_column = price_column
        self.use_adjusted = use_adjusted

    def prepare(self, frame: pd.DataFrame) -> pd.DataFrame:
        """전략 지표 계산에 사용할 signal_price 컬럼을 추가한다."""

        data = frame.copy()
        # 조정주가 사용 여부를 설정으로 명시해 결과 재현성을 높인다.
        selected_price = "adjusted_close" if self.use_adjusted else self.price_column
        if selected_price not in data.columns:
            raise DataValidationError(f"Price column '{selected_price}' does not exist.")
        # 지표/신호 계층은 어떤 원천 가격을 쓰든 signal_price만 참조한다.
        data["signal_price"] = data[selected_price].astype(float)
        return data.sort_values(["date", "ticker"]).reset_index(drop=True)
