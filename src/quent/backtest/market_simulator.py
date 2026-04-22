"""일봉 bar를 사용해 결정론적 체결을 시뮬레이션하는 모듈."""

from __future__ import annotations

from datetime import datetime
from math import floor

from quent.backtest.transaction_cost import TransactionCostModel
from quent.core.types import Fill, FillModel, Order, OrderSide


class MarketSimulator:
    """next open/next close 체결가와 슬리피지를 적용한다."""

    def __init__(
        self,
        fill_model: FillModel,
        cost_model: TransactionCostModel,
        slippage_bps: float,
    ) -> None:
        # 슬리피지는 bps 단위 설정값을 비율로 변환해 저장한다.
        if slippage_bps < 0:
            raise ValueError("slippage_bps must be non-negative.")
        self.fill_model = fill_model
        self.cost_model = cost_model
        self.slippage_rate = slippage_bps / 10_000.0

    def price_from_bar(self, bar: dict[str, object]) -> float:
        """fill_model에 따라 bar의 open 또는 close 가격을 선택한다."""

        column = "open" if self.fill_model == FillModel.NEXT_OPEN else "close"
        return float(bar[column])

    def fill(self, order: Order, bar: dict[str, object], filled_at: datetime) -> Fill:
        """주문 하나를 지정된 bar 가격으로 체결 처리한다."""

        base_price = self.price_from_bar(bar)
        # 매수는 불리하게 더 비싸게, 매도는 불리하게 더 싸게 체결한다.
        if order.side == OrderSide.BUY:
            fill_price = base_price * (1.0 + self.slippage_rate)
            slippage = fill_price - base_price
        else:
            fill_price = base_price * (1.0 - self.slippage_rate)
            slippage = base_price - fill_price
        # 수수료와 세금은 슬리피지가 반영된 실제 체결가 기준으로 계산한다.
        cost = self.cost_model.calculate(order.side, order.quantity, fill_price)
        return Fill(
            fill_id=f"fill_{order.order_id}",
            order_id=order.order_id,
            ticker=order.ticker,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            fee=cost.fee,
            tax=cost.tax,
            slippage=slippage,
            filled_at=filled_at,
        )

    def affordable_quantity(self, cash: float, price: float, desired_quantity: int) -> int:
        """현금, 슬리피지, 수수료를 모두 감안해 실제 매수 가능한 수량을 계산한다."""

        quantity = max(int(desired_quantity), 0)
        if quantity <= 0:
            return 0
        estimated_price = price * (1.0 + self.slippage_rate)
        # 먼저 가격만 기준으로 상한을 줄이고, 이후 비용까지 포함해 반복 보정한다.
        quantity = min(quantity, floor(cash / estimated_price))
        while quantity > 0:
            cost = self.cost_model.calculate(OrderSide.BUY, quantity, estimated_price)
            total_cash_needed = quantity * estimated_price + cost.fee + cost.tax
            if total_cash_needed <= cash:
                return quantity
            quantity -= 1
        return 0
