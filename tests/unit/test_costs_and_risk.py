from __future__ import annotations

from quent.backtest.transaction_cost import TransactionCostModel
from quent.core.types import OrderSide
from quent.portfolio.risk import RiskManager
from quent.portfolio.sizing import PositionSizer, SizingInput


def test_transaction_cost_applies_fee_and_sell_tax() -> None:
    # 1,000원 체결금액에 0.1% 수수료는 1원이고, 매도세 0.2%는 2원이다.
    model = TransactionCostModel(fee_rate=0.001, min_fee=1.0, tax_rate=0.002)

    buy = model.calculate(OrderSide.BUY, quantity=10, price=100)
    sell = model.calculate(OrderSide.SELL, quantity=10, price=100)

    assert buy.fee == 1.0
    assert buy.tax == 0.0
    assert sell.fee == 1.0
    assert sell.tax == 2.0


def test_position_sizer_equal_weight_respects_weight_limit() -> None:
    # equal_weight 목표는 50,000원이지만 종목당 25% 제한 때문에 25,000원만 허용된다.
    quantity = PositionSizer().calculate_quantity(
        SizingInput(
            method="equal_weight",
            equity=100_000,
            cash=100_000,
            price=100,
            max_positions=2,
            max_position_weight=0.25,
            fixed_fraction=0.5,
            fixed_notional=50_000,
        )
    )

    assert quantity == 250


def test_risk_manager_shrinks_quantity_to_position_weight() -> None:
    # 100,000원 equity의 25% 제한은 25,000원, 가격 100원이므로 최대 250주다.
    risk = RiskManager(
        max_position_weight=0.25,
        max_total_exposure=1.0,
        max_positions=4,
        max_daily_orders=20,
    )

    decision = risk.check_buy(
        quantity=1000,
        price=100,
        equity=100_000,
        current_exposure_value=0,
        open_positions=0,
        daily_orders=0,
    )

    assert decision.allowed
    assert decision.quantity == 250
