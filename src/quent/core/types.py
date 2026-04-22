"""주문, 체결, 포지션, 결과 객체처럼 시스템 전반에서 공유하는 도메인 타입."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class OrderSide(StrEnum):
    """주문 방향을 명확한 문자열 enum으로 제한한다."""

    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    """v1에서 지원하는 주문 유형."""

    MARKET = "market"


class OrderStatus(StrEnum):
    """주문 생명주기 상태."""

    NEW = "new"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    FAILED = "failed"


class PositionStatus(StrEnum):
    """포지션이 열려 있는지 닫혀 있는지 표시한다."""

    OPEN = "open"
    CLOSED = "closed"


class FillModel(StrEnum):
    """백테스트 체결 가격을 어느 bar 가격으로 잡을지 정한다."""

    NEXT_OPEN = "next_open"
    NEXT_CLOSE = "next_close"


@dataclass(slots=True)
class Order:
    """전략이 생성하고 브로커/시뮬레이터가 처리하는 주문 객체."""

    # order_id는 백테스트 로그와 브로커 상태 동기화의 기본 키다.
    order_id: str
    ticker: str
    side: OrderSide
    quantity: int
    created_at: datetime
    order_type: OrderType = OrderType.MARKET
    status: OrderStatus = OrderStatus.NEW
    idempotency_key: str | None = None
    reason: str = ""

    @property
    def is_terminal(self) -> bool:
        """더 이상 상태가 변하지 않는 최종 주문인지 확인한다."""

        return self.status in {
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.REJECTED,
            OrderStatus.FAILED,
        }


@dataclass(slots=True)
class Fill:
    """주문이 실제 또는 가상으로 체결된 결과."""

    fill_id: str
    order_id: str
    ticker: str
    side: OrderSide
    quantity: int
    price: float
    fee: float
    tax: float
    slippage: float
    filled_at: datetime

    @property
    def notional(self) -> float:
        """수수료/세금 제외 체결금액."""

        return self.quantity * self.price

    @property
    def cash_effect(self) -> float:
        """체결이 현금에 미치는 영향을 부호까지 포함해 계산한다."""

        if self.side == OrderSide.BUY:
            return -(self.notional + self.fee + self.tax)
        return self.notional - self.fee - self.tax


@dataclass(slots=True)
class Position:
    """단일 종목의 long 포지션 상태."""

    ticker: str
    quantity: int = 0
    avg_price: float = 0.0
    entry_time: datetime | None = None
    current_price: float = 0.0
    realized_pnl: float = 0.0
    status: PositionStatus = PositionStatus.CLOSED

    @property
    def market_value(self) -> float:
        """현재 평가금액."""

        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        """평균단가 기준 미실현 손익."""

        return self.quantity * (self.current_price - self.avg_price)

    def mark(self, price: float) -> None:
        """평가 가격을 최신 시장 가격으로 갱신한다."""

        self.current_price = float(price)


@dataclass(slots=True)
class PortfolioSnapshot:
    """특정 시점의 포트폴리오 요약 스냅샷."""

    date: datetime
    cash: float
    equity: float
    positions_value: float
    exposure: float
    positions: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class BacktestResult:
    """백테스트가 메모리와 파일로 남기는 핵심 결과 묶음."""

    run_id: str
    equity_curve: Any
    cash: Any
    positions: Any
    orders: Any
    fills: Any
    trades: Any
    metrics: dict[str, float | int | str | None]
    output_dir: str | None = None


@dataclass(slots=True)
class BrokerAccount:
    """브로커 계좌 상태를 표현하는 공통 타입."""

    cash: float
    equity: float
    buying_power: float
    currency: str = "KRW"
