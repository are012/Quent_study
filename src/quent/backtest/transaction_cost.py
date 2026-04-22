"""거래 수수료, 최소 수수료, 매도세를 계산하는 모듈."""

from __future__ import annotations

from dataclasses import dataclass

from quent.core.types import OrderSide


@dataclass(frozen=True, slots=True)
class TransactionCost:
    """체결 1건에 적용되는 비용 항목."""

    fee: float
    tax: float


class TransactionCostModel:
    """비율 수수료와 선택적 최소 수수료/매도세를 적용한다."""

    def __init__(self, fee_rate: float, min_fee: float = 0.0, tax_rate: float = 0.0) -> None:
        # 비용 값이 음수면 백테스트 수익률이 인위적으로 부풀려질 수 있다.
        if fee_rate < 0 or min_fee < 0 or tax_rate < 0:
            raise ValueError("Cost parameters must be non-negative.")
        self.fee_rate = fee_rate
        self.min_fee = min_fee
        self.tax_rate = tax_rate

    def calculate(self, side: OrderSide, quantity: int, price: float) -> TransactionCost:
        """체결 방향, 수량, 가격을 받아 실제 비용을 계산한다."""

        notional = quantity * price
        # 체결금액이 있을 때만 최소 수수료를 적용한다.
        fee = max(notional * self.fee_rate, self.min_fee if notional > 0 else 0.0)
        # 한국 주식 시장 가정처럼 세금은 기본적으로 매도에만 적용한다.
        tax = notional * self.tax_rate if side == OrderSide.SELL else 0.0
        return TransactionCost(fee=fee, tax=tax)
