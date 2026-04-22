"""목표 주문 수량을 계산하는 포지션 sizing 정책."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass(frozen=True, slots=True)
class SizingInput:
    """sizing 계산에 필요한 시장/계좌/설정 입력값."""

    method: str
    equity: float
    cash: float
    price: float
    max_positions: int
    max_position_weight: float
    fixed_fraction: float
    fixed_notional: float
    min_order_quantity: int = 1


class PositionSizer:
    """설정된 sizing 방식으로 목표 매수 수량을 계산한다."""

    def calculate_quantity(self, sizing: SizingInput) -> int:
        """금액 기반 목표를 정수 수량으로 변환한다."""

        if sizing.price <= 0:
            return 0
        # fixed_fraction은 현재 equity의 일정 비율을 목표 금액으로 쓴다.
        if sizing.method == "fixed_fraction":
            target_notional = sizing.equity * sizing.fixed_fraction
        # fixed_notional은 설정된 고정 금액만큼만 매수한다.
        elif sizing.method == "fixed_notional":
            target_notional = sizing.fixed_notional
        # equal_weight는 최대 보유 종목 수 기준으로 동일 비중을 목표로 한다.
        elif sizing.method == "equal_weight":
            target_notional = sizing.equity / sizing.max_positions
        else:
            raise ValueError(f"Unsupported sizing method: {sizing.method}")

        # 종목당 최대 비중과 사용 가능 현금을 넘지 않도록 목표 금액을 줄인다.
        target_notional = min(target_notional, sizing.equity * sizing.max_position_weight, sizing.cash)
        quantity = floor(target_notional / sizing.price)
        # 최소 주문 수량 미만이면 주문하지 않는다.
        return quantity if quantity >= sizing.min_order_quantity else 0
