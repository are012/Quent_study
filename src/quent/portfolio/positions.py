"""체결 이벤트를 기반으로 포지션과 실현 손익을 관리하는 모듈."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from quent.core.types import Fill, OrderSide, Position, PositionStatus


class PositionBook:
    """롱 온리 포지션과 청산 완료 거래를 추적한다."""

    def __init__(self) -> None:
        # positions는 ticker별 최신 포지션 상태를 보관한다.
        self.positions: dict[str, Position] = {}
        # trades는 매도 체결로 청산된 거래 단위 손익 로그다.
        self.trades: list[dict[str, object]] = []

    def get(self, ticker: str) -> Position:
        """없던 종목은 빈 포지션으로 반환해 호출부 분기를 줄인다."""

        return self.positions.get(ticker, Position(ticker=ticker))

    def open_positions(self) -> dict[str, Position]:
        """수량이 남아 있는 열린 포지션만 반환한다."""

        return {
            ticker: position
            for ticker, position in self.positions.items()
            if position.quantity > 0 and position.status == PositionStatus.OPEN
        }

    def apply_fill(self, fill: Fill) -> None:
        """체결 방향에 따라 평균단가, 수량, 실현 손익을 갱신한다."""

        position = self.get(fill.ticker)
        if fill.side == OrderSide.BUY:
            # 추가 매수가 들어와도 평균단가는 가중평균으로 관리한다.
            total_quantity = position.quantity + fill.quantity
            weighted_cost = position.avg_price * position.quantity + fill.price * fill.quantity
            position.avg_price = weighted_cost / total_quantity
            position.quantity = total_quantity
            position.entry_time = position.entry_time or fill.filled_at
            position.current_price = fill.price
            position.status = PositionStatus.OPEN
        else:
            # v1은 long-only이므로 보유 수량보다 많이 팔 수 없다.
            if fill.quantity > position.quantity:
                raise ValueError("Cannot sell more than current long position.")
            # 매도 시점에 실현 손익을 계산하고 거래 로그를 남긴다.
            realized = (fill.price - position.avg_price) * fill.quantity - fill.fee - fill.tax
            self.trades.append(
                {
                    "ticker": fill.ticker,
                    "entry_time": position.entry_time,
                    "exit_time": fill.filled_at,
                    "quantity": fill.quantity,
                    "entry_price": position.avg_price,
                    "exit_price": fill.price,
                    "fee": fill.fee,
                    "tax": fill.tax,
                    "pnl": realized,
                    "holding_days": _holding_days(position.entry_time, fill.filled_at),
                }
            )
            position.realized_pnl += realized
            position.quantity -= fill.quantity
            position.current_price = fill.price
            # 전량 청산되면 평균단가와 진입시점을 초기화한다.
            if position.quantity == 0:
                position.avg_price = 0.0
                position.entry_time = None
                position.status = PositionStatus.CLOSED
        self.positions[fill.ticker] = position

    def mark_to_market(self, prices: dict[str, float]) -> None:
        """현재 시장 가격으로 포지션 평가 가격을 갱신한다."""

        for ticker, price in prices.items():
            if ticker in self.positions:
                self.positions[ticker].mark(price)

    def positions_value(self) -> float:
        """열린 포지션의 총 평가금액을 계산한다."""

        return sum(position.market_value for position in self.open_positions().values())

    def quantities(self) -> dict[str, int]:
        """열린 포지션의 ticker별 수량만 반환한다."""

        return {ticker: position.quantity for ticker, position in self.open_positions().items()}

    def rows(self, date: datetime, cash: float, equity: float) -> list[dict[str, object]]:
        """리포팅용 일별 포지션 row를 만든다."""

        rows: list[dict[str, object]] = []
        for position in self.open_positions().values():
            row = asdict(position)
            row.update(
                {
                    "date": date,
                    "cash": cash,
                    "equity": equity,
                    "market_value": position.market_value,
                    "unrealized_pnl": position.unrealized_pnl,
                }
            )
            rows.append(row)
        return rows


def _holding_days(entry_time: datetime | None, exit_time: datetime) -> int | None:
    """진입일과 청산일 사이의 보유 일수를 계산한다."""

    if entry_time is None:
        return None
    return max((exit_time.date() - entry_time.date()).days, 0)
