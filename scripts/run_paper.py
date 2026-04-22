#!/usr/bin/env python
"""Paper broker를 초기화해 계좌 상태 조회가 되는지 확인하는 스크립트."""

from __future__ import annotations

import sys
from pathlib import Path

# 스크립트를 repo root 밖에서 실행해도 src 패키지를 찾도록 경로를 보정한다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quent.backtest.market_simulator import MarketSimulator
from quent.backtest.transaction_cost import TransactionCostModel
from quent.config import load_config
from quent.core.types import FillModel
from quent.execution.paper_broker import PaperBroker


def main() -> int:
    """설정 파일을 읽어 paper broker와 체결 시뮬레이터를 만든다."""

    config = load_config(PROJECT_ROOT / "config" / "strategy.yaml")
    # paper broker는 백테스트와 같은 MarketSimulator를 재사용할 수 있다.
    simulator = MarketSimulator(
        fill_model=FillModel.NEXT_OPEN,
        cost_model=TransactionCostModel(config.execution.fee_rate, config.execution.min_fee),
        slippage_bps=config.execution.slippage_bps,
    )
    # 실제 주문 없이 메모리 장부만 가진 브로커를 만든다.
    broker = PaperBroker(config.strategy.initial_capital, simulator)
    print(broker.get_account())
    return 0


if __name__ == "__main__":
    # shell에서 실행했을 때 정상/오류 종료 코드를 명확히 전달한다.
    raise SystemExit(main())
