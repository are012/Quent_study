"""백테스트 엔진이 요구하는 중간 데이터 컬럼을 검증하는 헬퍼."""

from __future__ import annotations

import pandas as pd

from quent.core.exceptions import DataValidationError


def assert_required_signal_columns(frame: pd.DataFrame) -> None:
    """신호 생성 이후 엔진이 필요한 컬럼들이 존재하는지 확인한다."""

    # 이 컬럼이 없으면 주문 시점과 평가 시점을 안전하게 구분할 수 없다.
    missing = {"date", "ticker", "open", "close", "executable_signal", "raw_signal"} - set(
        frame.columns
    )
    if missing:
        raise DataValidationError(f"Missing signal columns: {sorted(missing)}")
