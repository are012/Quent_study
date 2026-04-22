"""프로세스 재시작 후 복구를 위한 JSON 상태 저장소."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quent.core.exceptions import StateStoreError


class StateStore:
    """로컬 실행 상태를 JSON 파일로 저장하고 브로커 상태와 비교한다."""

    def __init__(self, path: str | Path) -> None:
        # path는 paper/live 실행 루프가 공유하는 상태 파일 위치다.
        self.path = Path(path)

    def save(self, state: dict[str, Any]) -> None:
        """상태 dict를 JSON 파일에 저장한다."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.path.open("w", encoding="utf-8") as handle:
                json.dump(state, handle, indent=2, ensure_ascii=False, default=str)
        except OSError as exc:
            raise StateStoreError(f"Could not save state to {self.path}") from exc

    def load(self) -> dict[str, Any]:
        """상태 파일이 있으면 읽고, 없으면 빈 상태를 반환한다."""

        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise StateStoreError(f"Could not load state from {self.path}") from exc
        if not isinstance(loaded, dict):
            raise StateStoreError("Stored state must be a JSON object.")
        return loaded

    def reconcile(self, broker_state: dict[str, Any]) -> dict[str, Any]:
        """로컬 상태와 브로커 상태가 다르면 safe_mode를 켠 결과를 반환한다."""

        local_state = self.load()
        # 둘 다 존재하는데 다르면 신규 주문을 막아야 하는 보호 상태로 본다.
        safe_mode = bool(local_state and broker_state and local_state != broker_state)
        return {
            "local_state": local_state,
            "broker_state": broker_state,
            "safe_mode": safe_mode,
        }
