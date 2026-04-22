"""체결 이벤트가 현금에 미치는 영향을 관리하는 모듈."""

from __future__ import annotations

from quent.core.types import Fill


class CashLedger:
    """사용 가능 현금을 추적한다."""

    def __init__(self, initial_cash: float) -> None:
        # 초기 자본은 0보다 커야 포지션 sizing과 수익률 계산이 가능하다.
        if initial_cash <= 0:
            raise ValueError("initial_cash must be positive.")
        self.cash = float(initial_cash)

    def apply_fill(self, fill: Fill) -> None:
        """체결의 cash_effect를 현금 장부에 반영한다."""

        self.cash += fill.cash_effect
