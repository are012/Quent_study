"""파일/API 원천에서 데이터를 읽어오는 로더 모듈."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from quent.data.validators import OhlcvValidator


class CsvLongDataLoader:
    """long-format OHLCV CSV를 읽고 검증기까지 통과시킨다."""

    def __init__(self, validator: OhlcvValidator | None = None) -> None:
        # 테스트나 확장 로더에서 검증 규칙을 주입할 수 있게 한다.
        self.validator = validator or OhlcvValidator()

    def load(self, path: str | Path) -> pd.DataFrame:
        """CSV 파일을 읽고 컬럼명을 표준화한 뒤 OHLCV 검증을 수행한다."""

        frame = pd.read_csv(path)
        # 사용자가 Date, CLOSE처럼 써도 내부에서는 소문자 표준 컬럼으로 처리한다.
        frame.columns = [str(column).strip().lower() for column in frame.columns]
        return self.validator.validate(frame)
