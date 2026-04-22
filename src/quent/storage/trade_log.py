"""거래 이벤트를 JSON lines 형식으로 누적 저장하는 로그."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TradeLog:
    """실행 중 발생한 거래 row를 append-only 방식으로 남긴다."""

    def __init__(self, path: str | Path) -> None:
        # append-only 로그는 감사 추적과 장애 분석에 유리하다.
        self.path = Path(path)

    def append(self, row: dict[str, Any]) -> None:
        """단일 거래 row를 JSON 한 줄로 추가한다."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
