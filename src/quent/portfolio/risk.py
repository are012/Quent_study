"""주문 생성 전에 포트폴리오 리스크 제한을 적용하는 모듈."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RiskDecision:
    """리스크 검사를 통과했는지와 조정된 수량을 담는다."""

    allowed: bool
    quantity: int
    reason: str = ""


class RiskManager:
    """롱 온리 전략에 필요한 보수적인 리스크 제한을 적용한다."""

    def __init__(
        self,
        max_position_weight: float,
        max_total_exposure: float,
        max_positions: int,
        max_daily_orders: int,
        min_order_notional: float = 0.0,
    ) -> None:
        # 모든 제한값은 config/risk.yaml에서 주입된다.
        self.max_position_weight = max_position_weight
        self.max_total_exposure = max_total_exposure
        self.max_positions = max_positions
        self.max_daily_orders = max_daily_orders
        self.min_order_notional = min_order_notional

    def check_buy(
        self,
        quantity: int,
        price: float,
        equity: float,
        current_exposure_value: float,
        open_positions: int,
        daily_orders: int,
    ) -> RiskDecision:
        """매수 주문이 노출도/보유종목/일일주문 제한을 만족하는지 확인한다."""

        # 하루 주문 수 제한은 과도한 whipsaw나 오류성 반복 주문을 막는다.
        if daily_orders >= self.max_daily_orders:
            return RiskDecision(False, 0, "daily order limit reached")
        if quantity <= 0:
            return RiskDecision(False, 0, "quantity is zero")
        if open_positions >= self.max_positions:
            return RiskDecision(False, 0, "max positions reached")

        # 종목 단위와 포트폴리오 단위 노출 제한을 동시에 만족해야 한다.
        max_position_value = equity * self.max_position_weight
        max_total_value = equity * self.max_total_exposure - current_exposure_value
        allowed_notional = max(0.0, min(max_position_value, max_total_value))
        adjusted_quantity = min(quantity, int(allowed_notional // price))
        if adjusted_quantity <= 0:
            return RiskDecision(False, 0, "exposure limit reached")
        # 거래소/브로커 최소 주문 금액을 만족하지 못하면 거부한다.
        if adjusted_quantity * price < self.min_order_notional:
            return RiskDecision(False, 0, "below minimum order notional")
        return RiskDecision(True, adjusted_quantity)

    def check_sell(self, quantity: int, daily_orders: int) -> RiskDecision:
        """매도 주문은 수량과 일일 주문 수만 검증한다."""

        if daily_orders >= self.max_daily_orders:
            return RiskDecision(False, 0, "daily order limit reached")
        if quantity <= 0:
            return RiskDecision(False, 0, "quantity is zero")
        return RiskDecision(True, quantity)
