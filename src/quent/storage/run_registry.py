"""백테스트/실행 run 메타데이터를 누적 기록하는 registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RunRegistry:
    """run_id, 설정, 산출물 위치 같은 실행 메타데이터를 남긴다."""

    def __init__(self, path: str | Path) -> None:
        # registry도 JSONL로 두면 여러 실행을 한 파일에 순서대로 기록할 수 있다.
        self.path = Path(path)

    def append(self, row: dict[str, Any]) -> None:
        """단일 run 메타데이터 row를 추가한다."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
