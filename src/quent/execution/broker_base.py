"""백테스트/페이퍼/실거래 계층이 공유하는 브로커 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from quent.core.types import BrokerAccount, Order, Position


class BrokerBase(ABC):
    """PaperBroker와 live adapter가 반드시 구현해야 하는 공통 계약."""

    @abstractmethod
    def get_account(self) -> BrokerAccount:
        """계좌 현금, 총자산, 매수 가능 금액을 조회한다."""

        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> dict[str, Position]:
        """브로커가 인식하는 현재 포지션을 조회한다."""

        raise NotImplementedError

    @abstractmethod
    def submit_order(self, order: Order) -> Order:
        """주문을 제출하고 브로커가 받은 주문 상태를 반환한다."""

        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str) -> Order:
        """미체결 주문을 취소한다."""

        raise NotImplementedError

    @abstractmethod
    def get_order_status(self, order_id: str):
        """특정 주문의 최신 상태를 조회한다."""

        raise NotImplementedError

    @abstractmethod
    def sync_state(self) -> dict[str, object]:
        """로컬 상태와 비교할 브로커 상태 스냅샷을 반환한다."""

        raise NotImplementedError
