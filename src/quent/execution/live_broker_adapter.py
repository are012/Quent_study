"""한국투자증권(KIS) 실거래 API를 붙이기 위한 안전한 어댑터 골격."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

from quent.config import BrokerConfig
from quent.core.exceptions import BrokerError
from quent.core.types import BrokerAccount, Order, OrderStatus, Position
from quent.execution.broker_base import BrokerBase

# 실제 HTTP 클라이언트는 테스트 가능하도록 함수 형태로 주입한다.
Transport = Callable[[str, str, dict[str, Any]], dict[str, Any]]


class KisLiveBrokerAdapter(BrokerBase):
    """KIS REST API 경계를 감싸는 live broker adapter.

    v1은 안전을 위해 기본 dry-run이며, 명시적으로 dry_run을 끄고 transport를 주입해야
    실제 요청 경로가 열린다.
    """

    def __init__(self, config: BrokerConfig, transport: Transport | None = None) -> None:
        # config는 인증 환경변수 이름, retry, dry-run 여부를 포함한다.
        self.config = config
        self.transport = transport
        self.orders: dict[str, Order] = {}
        self.idempotency_index: dict[str, str] = {}

    def validate_credentials(self) -> None:
        """KIS 호출에 필요한 환경변수가 모두 있는지 확인한다."""

        missing = [
            env_name
            for env_name in (
                self.config.account_id_env,
                self.config.app_key_env,
                self.config.app_secret_env,
                self.config.token_env,
            )
            if not os.getenv(env_name)
        ]
        if missing:
            raise BrokerError(f"Missing KIS credential environment variables: {missing}")

    def get_account(self) -> BrokerAccount:
        """계좌 정보를 조회한다. dry-run에서는 0원 계좌를 반환해 실주문을 막는다."""

        if self.config.dry_run:
            return BrokerAccount(cash=0.0, equity=0.0, buying_power=0.0, currency="KRW")
        response = self._request("GET", "/uapi/domestic-stock/v1/trading/inquire-balance", {})
        return self._parse_account(response)

    def get_positions(self) -> dict[str, Position]:
        """보유 포지션을 조회한다. dry-run에서는 빈 포지션을 반환한다."""

        if self.config.dry_run:
            return {}
        response = self._request("GET", "/uapi/domestic-stock/v1/trading/inquire-balance", {})
        return self._parse_positions(response)

    def submit_order(self, order: Order) -> Order:
        """주문을 제출한다. idempotency_key가 같으면 기존 주문을 반환한다."""

        if order.idempotency_key and order.idempotency_key in self.idempotency_index:
            return self.orders[self.idempotency_index[order.idempotency_key]]
        # dry-run은 실제 네트워크 요청 없이 주문 접수 상태만 기록한다.
        if self.config.dry_run:
            order.status = OrderStatus.SUBMITTED
            self.orders[order.order_id] = order
            if order.idempotency_key:
                self.idempotency_index[order.idempotency_key] = order.order_id
            return order

        # live 주문 전에는 인증 정보가 모두 준비됐는지 강제로 검증한다.
        self.validate_credentials()
        payload = {
            "ticker": order.ticker,
            "side": order.side.value,
            "quantity": order.quantity,
            "order_type": order.order_type.value,
            "idempotency_key": order.idempotency_key,
        }
        self._request("POST", "/uapi/domestic-stock/v1/trading/order-cash", payload)
        order.status = OrderStatus.SUBMITTED
        self.orders[order.order_id] = order
        if order.idempotency_key:
            self.idempotency_index[order.idempotency_key] = order.order_id
        return order

    def cancel_order(self, order_id: str) -> Order:
        """주문 취소 요청을 보낸다. dry-run에서는 로컬 상태만 변경한다."""

        order = self.orders[order_id]
        if self.config.dry_run:
            order.status = OrderStatus.CANCELED
            return order
        self._request("POST", "/uapi/domestic-stock/v1/trading/order-rvsecncl", {"order_id": order_id})
        order.status = OrderStatus.CANCELED
        return order

    def get_order_status(self, order_id: str) -> OrderStatus:
        """로컬에 저장된 주문 상태를 반환한다."""

        return self.orders[order_id].status

    def sync_state(self) -> dict[str, object]:
        """계좌, 포지션, 주문 상태를 한 번에 묶어 복구 검증용으로 반환한다."""

        return {
            "account": self.get_account(),
            "positions": self.get_positions(),
            "orders": self.orders,
        }

    def _request(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """주입된 transport로 KIS 요청을 보내고 실패 시 재시도한다."""

        if self.transport is None:
            raise BrokerError("No transport configured for live KIS adapter.")
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                # transport는 HTTP 세부 구현을 숨기고 테스트에서는 mock으로 대체된다.
                response = self.transport(method, path, payload)
                if not isinstance(response, dict):
                    raise BrokerError("Broker response must be a mapping.")
                return response
            except Exception as exc:  # pragma: no cover - exercised through adapter tests
                last_error = exc
                if attempt < self.config.max_retries:
                    # 간단한 exponential backoff로 일시 장애에 대응한다.
                    time.sleep(min(0.25 * (2**attempt), 2.0))
        raise BrokerError("KIS request failed after retries.") from last_error

    def _parse_account(self, response: dict[str, Any]) -> BrokerAccount:
        """KIS 잔고 응답을 공통 BrokerAccount 타입으로 변환한다."""

        try:
            # KIS 잔고 API는 output2에 계좌 요약이 들어오는 형태를 기본 가정으로 둔다.
            output = response.get("output2", [{}])[0] if isinstance(response.get("output2"), list) else response
            cash = float(output.get("dnca_tot_amt", 0.0))
            equity = float(output.get("tot_evlu_amt", cash))
        except (TypeError, ValueError) as exc:
            raise BrokerError("Could not parse KIS account response.") from exc
        return BrokerAccount(cash=cash, equity=equity, buying_power=cash, currency="KRW")

    def _parse_positions(self, response: dict[str, Any]) -> dict[str, Position]:
        """KIS 보유 종목 응답을 ticker별 Position으로 변환한다."""

        positions: dict[str, Position] = {}
        rows = response.get("output1", [])
        if not isinstance(rows, list):
            raise BrokerError("Could not parse KIS positions response.")
        for row in rows:
            # pdno는 종목코드, hldg_qty는 보유수량으로 가정한다.
            ticker = str(row.get("pdno", ""))
            quantity = int(float(row.get("hldg_qty", 0)))
            if not ticker or quantity <= 0:
                continue
            position = Position(
                ticker=ticker,
                quantity=quantity,
                avg_price=float(row.get("pchs_avg_pric", 0.0)),
                current_price=float(row.get("prpr", 0.0)),
            )
            positions[ticker] = position
        return positions
