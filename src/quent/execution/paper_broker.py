"""메모리 기반 paper broker 구현."""

from __future__ import annotations

from datetime import datetime

from quent.backtest.market_simulator import MarketSimulator
from quent.core.types import BrokerAccount, Fill, Order, OrderStatus, Position
from quent.execution.broker_base import BrokerBase
from quent.portfolio.cash import CashLedger
from quent.portfolio.positions import PositionBook


class PaperBroker(BrokerBase):
    """실제 주문 없이 주문 상태와 체결을 시뮬레이션한다."""

    def __init__(self, initial_cash: float, simulator: MarketSimulator) -> None:
        # paper broker도 백테스트와 같은 현금/포지션 장부를 사용한다.
        self.cash = CashLedger(initial_cash)
        self.positions = PositionBook()
        self.simulator = simulator
        self.orders: dict[str, Order] = {}
        self.idempotency_index: dict[str, str] = {}
        self.fills: list[Fill] = []

    def get_account(self) -> BrokerAccount:
        """현재 현금과 포지션 평가금액으로 계좌 상태를 계산한다."""

        positions_value = self.positions.positions_value()
        equity = self.cash.cash + positions_value
        return BrokerAccount(cash=self.cash.cash, equity=equity, buying_power=self.cash.cash)

    def get_positions(self) -> dict[str, Position]:
        """열린 포지션만 반환한다."""

        return self.positions.open_positions()

    def submit_order(self, order: Order) -> Order:
        """주문을 접수하고 idempotency_key로 중복 제출을 막는다."""

        if order.idempotency_key and order.idempotency_key in self.idempotency_index:
            return self.orders[self.idempotency_index[order.idempotency_key]]
        order.status = OrderStatus.SUBMITTED
        self.orders[order.order_id] = order
        if order.idempotency_key:
            self.idempotency_index[order.idempotency_key] = order.order_id
        return order

    def cancel_order(self, order_id: str) -> Order:
        """최종 상태가 아닌 주문만 취소 상태로 바꾼다."""

        order = self.orders[order_id]
        if not order.is_terminal:
            order.status = OrderStatus.CANCELED
        return order

    def get_order_status(self, order_id: str) -> OrderStatus:
        """저장된 주문 상태를 반환한다."""

        return self.orders[order_id].status

    def sync_state(self) -> dict[str, object]:
        """재시작 복구 검증에 사용할 paper broker 상태를 반환한다."""

        return {
            "account": self.get_account(),
            "positions": self.get_positions(),
            "open_orders": {
                order_id: order
                for order_id, order in self.orders.items()
                if not order.is_terminal
            },
        }

    def process_market_bar(self, order_id: str, bar: dict[str, object], timestamp: datetime) -> Fill:
        """접수된 주문을 주어진 bar로 체결시키고 장부에 반영한다."""

        order = self.orders[order_id]
        fill = self.simulator.fill(order, bar, timestamp)
        self.cash.apply_fill(fill)
        self.positions.apply_fill(fill)
        order.status = OrderStatus.FILLED
        self.fills.append(fill)
        return fill
