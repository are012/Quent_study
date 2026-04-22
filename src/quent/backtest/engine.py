"""일봉 데이터를 날짜 순서대로 처리하는 순차형 백테스트 엔진."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from quent.backtest.market_simulator import MarketSimulator
from quent.backtest.transaction_cost import TransactionCostModel
from quent.backtest.validators import assert_required_signal_columns
from quent.config import ConfigBundle
from quent.core.clock import make_run_id
from quent.core.types import BacktestResult, Fill, Order, OrderSide, OrderStatus
from quent.data.adapters import MarketDataAdapter
from quent.portfolio.cash import CashLedger
from quent.portfolio.positions import PositionBook
from quent.portfolio.risk import RiskManager
from quent.portfolio.sizing import PositionSizer, SizingInput
from quent.reporting.exporters import BacktestExporter
from quent.signals.ma_crossover import MovingAverageCrossoverSignalGenerator
from quent.analytics.metrics import calculate_metrics


class BacktestEngine:
    """롱 온리 이동평균 교차 전략을 재현 가능하게 실행한다."""

    def __init__(self, config: ConfigBundle, run_id: str | None = None) -> None:
        # 설정과 run_id는 모든 산출물의 재현성을 추적하는 기준이다.
        self.config = config
        self.run_id = run_id or make_run_id("backtest")
        # 데이터 어댑터는 close/adjusted_close 선택을 signal_price로 표준화한다.
        self.adapter = MarketDataAdapter(
            price_column=config.strategy.price_column,
            use_adjusted=config.strategy.use_adjusted,
        )
        self.signal_generator = MovingAverageCrossoverSignalGenerator(
            short_window=config.strategy.short_window,
            long_window=config.strategy.long_window,
            ma_type=config.strategy.ma_type,
        )
        # 체결 시뮬레이터는 fill model, 수수료, 슬리피지를 한 곳에서 적용한다.
        self.simulator = MarketSimulator(
            fill_model=config.execution.fill_model,
            cost_model=TransactionCostModel(
                fee_rate=config.execution.fee_rate,
                min_fee=config.execution.min_fee,
                tax_rate=config.execution.tax_rate,
            ),
            slippage_bps=config.execution.slippage_bps,
        )
        # sizing과 risk는 분리해, 목표 수량 계산과 제한 적용을 독립적으로 테스트한다.
        self.sizer = PositionSizer()
        self.risk = RiskManager(
            max_position_weight=config.risk.max_position_weight,
            max_total_exposure=config.risk.max_total_exposure,
            max_positions=config.risk.max_positions,
            max_daily_orders=config.risk.max_daily_orders,
            min_order_notional=config.execution.min_order_notional,
        )

    def run(self, market_data: pd.DataFrame, output_dir: str | Path | None = None) -> BacktestResult:
        """입력 데이터를 신호, 주문, 체결, 포트폴리오 평가, 리포트까지 처리한다."""

        # 원본 OHLCV를 전략이 쓰는 표준 형태로 변환한다.
        prepared = self.adapter.prepare(market_data)
        # raw signal은 당일 종가 기준, executable signal은 하루 지연된 값이다.
        data = self.signal_generator.generate(prepared)
        # 백테스트 엔진이 기대하는 컬럼이 모두 있는지 실행 초기에 확인한다.
        assert_required_signal_columns(data)

        # 현금 장부와 포지션 장부는 체결 이벤트를 통해서만 변한다.
        cash = CashLedger(self.config.strategy.initial_capital)
        positions = PositionBook()

        # 아래 리스트들은 최종 CSV/JSON 산출물의 원천 데이터다.
        equity_rows: list[dict[str, Any]] = []
        cash_rows: list[dict[str, Any]] = []
        position_rows: list[dict[str, Any]] = []
        order_rows: list[dict[str, Any]] = []
        fill_rows: list[dict[str, Any]] = []
        event_rows: list[dict[str, Any]] = []

        # 날짜별로 묶어 실제 일봉 운용처럼 시간 순서대로만 진행한다.
        grouped = {date: group for date, group in data.groupby("date", sort=True)}
        for date, day_frame in grouped.items():
            current_dt = _to_datetime(date)
            # 같은 날짜의 여러 종목 bar를 ticker로 바로 찾을 수 있게 바꾼다.
            day_rows = {
                str(row.ticker): row._asdict()
                for row in day_frame.itertuples(index=False)
            }

            # 주문은 당일 시가 기준으로 체결되고, 평가는 당일 종가 기준으로 이뤄진다.
            open_prices = {ticker: float(row["open"]) for ticker, row in day_rows.items()}
            close_prices = {ticker: float(row["close"]) for ticker, row in day_rows.items()}
            positions.mark_to_market(open_prices)
            # 하루 주문 수 제한을 위해 날짜가 바뀔 때마다 카운터를 초기화한다.
            daily_orders = 0

            for ticker in sorted(day_rows):
                row = day_rows[ticker]
                # executable_signal은 전일 종가로 이미 확정된 오늘의 목표 보유 상태다.
                target_long = bool(row["executable_signal"])
                position = positions.get(ticker)
                # 목표가 long이고 보유가 없을 때만 신규 매수한다.
                if target_long and position.quantity == 0:
                    order = self._build_buy_order(
                        ticker=ticker,
                        bar=row,
                        cash=cash.cash,
                        positions=positions,
                        created_at=current_dt,
                        daily_orders=daily_orders,
                    )
                # 목표가 flat이고 보유가 있으면 전량 청산한다.
                elif not target_long and position.quantity > 0:
                    order = self._build_sell_order(
                        ticker=ticker,
                        quantity=position.quantity,
                        created_at=current_dt,
                        daily_orders=daily_orders,
                    )
                else:
                    # 이미 목표 상태와 실제 포지션이 일치하면 주문을 내지 않는다.
                    order = None

                if order is None:
                    continue
                daily_orders += 1
                # v1 백테스트는 accepted order가 항상 즉시 체결된다고 가정한다.
                order.status = OrderStatus.FILLED
                fill = self.simulator.fill(order, row, current_dt)
                # 체결이 발생하면 현금과 포지션 장부를 같은 이벤트로 갱신한다.
                cash.apply_fill(fill)
                positions.apply_fill(fill)
                # 주문/체결/event 로그를 분리 저장해 감사 추적이 가능하게 한다.
                order_rows.append(_order_to_row(order))
                fill_rows.append(_fill_to_row(fill))
                event_rows.append(
                    {
                        "timestamp": current_dt.isoformat(),
                        "run_id": self.run_id,
                        "event": "fill",
                        "ticker": fill.ticker,
                        "order_id": fill.order_id,
                        "side": fill.side.value,
                        "quantity": fill.quantity,
                        "price": fill.price,
                    }
                )

            # 모든 주문 처리 후 종가로 포지션을 평가해 일별 equity를 확정한다.
            positions.mark_to_market(close_prices)
            positions_value = positions.positions_value()
            equity = cash.cash + positions_value
            exposure = positions_value / equity if equity else 0.0
            equity_rows.append(
                {
                    "date": current_dt,
                    "equity": equity,
                    "positions_value": positions_value,
                    "exposure": exposure,
                }
            )
            cash_rows.append({"date": current_dt, "cash": cash.cash, "cash_weight": cash.cash / equity})
            position_rows.extend(positions.rows(current_dt, cash.cash, equity))

        # 누적된 row들을 DataFrame으로 바꿔 분석/저장 계층에 넘긴다.
        equity_df = pd.DataFrame(equity_rows)
        cash_df = pd.DataFrame(cash_rows)
        positions_df = pd.DataFrame(position_rows)
        orders_df = pd.DataFrame(order_rows)
        fills_df = pd.DataFrame(fill_rows)
        trades_df = pd.DataFrame(positions.trades)
        # 성과지표는 백테스트 엔진에서 계산하지 않고 analytics 계층에 위임한다.
        metrics = calculate_metrics(
            equity_curve=equity_df,
            cash=cash_df,
            fills=fills_df,
            trades=trades_df,
            market_data=data,
            initial_capital=self.config.strategy.initial_capital,
            benchmark=self.config.strategy.benchmark,
        )

        # BacktestResult는 메모리 결과와 저장 경로를 함께 들고 다니는 반환 객체다.
        result = BacktestResult(
            run_id=self.run_id,
            equity_curve=equity_df,
            cash=cash_df,
            positions=positions_df,
            orders=orders_df,
            fills=fills_df,
            trades=trades_df,
            metrics=metrics,
        )
        if output_dir is not None:
            # output_dir이 지정된 경우에만 파일 시스템에 산출물을 쓴다.
            exporter = BacktestExporter(output_dir)
            exporter.export(result, self.config, event_rows)
            result.output_dir = str(exporter.output_dir)
        return result

    def _build_buy_order(
        self,
        ticker: str,
        bar: dict[str, object],
        cash: float,
        positions: PositionBook,
        created_at: datetime,
        daily_orders: int,
    ) -> Order | None:
        """매수 목표가 생겼을 때 sizing, 현금, 리스크 제한을 모두 반영해 주문을 만든다."""

        open_price = float(bar["open"])
        positions_value = positions.positions_value()
        equity = cash + positions_value
        # 먼저 전략의 sizing 방식으로 원하는 수량을 계산한다.
        desired_quantity = self.sizer.calculate_quantity(
            SizingInput(
                method=self.config.strategy.sizing_method,
                equity=equity,
                cash=cash,
                price=open_price,
                max_positions=self.config.risk.max_positions,
                max_position_weight=self.config.risk.max_position_weight,
                fixed_fraction=self.config.strategy.fixed_fraction,
                fixed_notional=self.config.strategy.fixed_notional,
                min_order_quantity=self.config.execution.min_order_quantity,
            )
        )
        # 수수료와 슬리피지까지 감안해 실제 현금으로 살 수 있는 수량으로 줄인다.
        affordable_quantity = self.simulator.affordable_quantity(cash, open_price, desired_quantity)
        # 포트폴리오 리스크 제한을 마지막으로 적용한다.
        decision = self.risk.check_buy(
            quantity=affordable_quantity,
            price=open_price,
            equity=equity,
            current_exposure_value=positions_value,
            open_positions=len(positions.open_positions()),
            daily_orders=daily_orders,
        )
        if not decision.allowed:
            return None
        # idempotency_key는 live adapter에서도 중복 주문 방지 기준으로 쓸 수 있다.
        return Order(
            order_id=f"{self.run_id}_{created_at.strftime('%Y%m%d')}_{ticker}_buy",
            ticker=ticker,
            side=OrderSide.BUY,
            quantity=decision.quantity,
            created_at=created_at,
            idempotency_key=f"{self.run_id}:{created_at.date()}:{ticker}:buy",
            reason="ma executable long",
        )

    def _build_sell_order(
        self,
        ticker: str,
        quantity: int,
        created_at: datetime,
        daily_orders: int,
    ) -> Order | None:
        """청산 목표가 생겼을 때 보유 수량 전량 매도 주문을 만든다."""

        decision = self.risk.check_sell(quantity, daily_orders)
        if not decision.allowed:
            return None
        return Order(
            order_id=f"{self.run_id}_{created_at.strftime('%Y%m%d')}_{ticker}_sell",
            ticker=ticker,
            side=OrderSide.SELL,
            quantity=decision.quantity,
            created_at=created_at,
            idempotency_key=f"{self.run_id}:{created_at.date()}:{ticker}:sell",
            reason="ma executable flat",
        )


def _to_datetime(value: object) -> datetime:
    """pandas Timestamp/날짜 값을 표준 datetime으로 변환한다."""

    return pd.Timestamp(value).to_pydatetime()


def _order_to_row(order: Order) -> dict[str, object]:
    """Order dataclass를 CSV 저장에 적합한 dict로 바꾼다."""

    row = asdict(order)
    row["side"] = order.side.value
    row["order_type"] = order.order_type.value
    row["status"] = order.status.value
    return row


def _fill_to_row(fill: Fill) -> dict[str, object]:
    """Fill dataclass에 notional/cash_effect 파생값을 더해 dict로 바꾼다."""

    row = asdict(fill)
    row["side"] = fill.side.value
    row["notional"] = fill.notional
    row["cash_effect"] = fill.cash_effect
    return row
