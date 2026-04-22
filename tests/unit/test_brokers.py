from __future__ import annotations

from datetime import datetime

from quent.backtest.market_simulator import MarketSimulator
from quent.backtest.transaction_cost import TransactionCostModel
from quent.config import BrokerConfig
from quent.core.types import FillModel, Order, OrderSide, OrderStatus
from quent.execution.live_broker_adapter import KisLiveBrokerAdapter
from quent.execution.paper_broker import PaperBroker


def test_paper_broker_idempotency_and_fill() -> None:
    # 슬리피지와 수수료를 0으로 둬 체결금액과 현금 변화를 손으로 검증하기 쉽게 한다.
    simulator = MarketSimulator(FillModel.NEXT_OPEN, TransactionCostModel(0.0), slippage_bps=0)
    broker = PaperBroker(1000, simulator)
    order = Order(
        order_id="o1",
        ticker="AAA",
        side=OrderSide.BUY,
        quantity=10,
        created_at=datetime(2024, 1, 2),
        idempotency_key="same",
    )

    # 같은 idempotency_key로 제출하면 두 번째 주문은 새 주문이 아니라 기존 주문이어야 한다.
    first = broker.submit_order(order)
    second = broker.submit_order(
        Order(
            order_id="o2",
            ticker="AAA",
            side=OrderSide.BUY,
            quantity=10,
            created_at=datetime(2024, 1, 2),
            idempotency_key="same",
        )
    )
    # next_open 모델이므로 open=10 가격에 10주가 체결된다.
    fill = broker.process_market_bar("o1", {"open": 10.0, "close": 10.5}, datetime(2024, 1, 2))

    assert first.order_id == second.order_id
    assert broker.get_order_status("o1") == OrderStatus.FILLED
    assert fill.notional == 100.0
    assert broker.get_account().cash == 900.0


def test_kis_adapter_dry_run_does_not_require_credentials() -> None:
    # dry-run 모드는 인증 환경변수 없이도 주문 접수 경로를 검증할 수 있어야 한다.
    broker = KisLiveBrokerAdapter(BrokerConfig(dry_run=True))
    order = Order(
        order_id="o1",
        ticker="005930",
        side=OrderSide.BUY,
        quantity=1,
        created_at=datetime(2024, 1, 2),
        idempotency_key="dry",
    )

    submitted = broker.submit_order(order)

    assert submitted.status == OrderStatus.SUBMITTED
    assert broker.get_account().currency == "KRW"


def test_kis_adapter_uses_injected_transport() -> None:
    # 실제 HTTP 대신 transport 함수를 주입해 응답 파싱만 테스트한다.
    calls = []

    def transport(method, path, payload):
        calls.append((method, path, payload))
        return {"output2": [{"dnca_tot_amt": "1000", "tot_evlu_amt": "1200"}]}

    broker = KisLiveBrokerAdapter(BrokerConfig(dry_run=False), transport=transport)
    account = broker.get_account()

    assert account.cash == 1000.0
    assert account.equity == 1200.0
    assert calls
