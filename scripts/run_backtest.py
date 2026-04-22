#!/usr/bin/env python
"""CLI에서 이동평균 추세추종 백테스트를 실행하는 스크립트."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 스크립트를 설치 없이 바로 실행해도 src 패키지를 찾을 수 있게 경로를 추가한다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quent.analytics.tearsheet import format_metric_summary
from quent.backtest.engine import BacktestEngine
from quent.config import load_config
from quent.data.loaders import CsvLongDataLoader


def main() -> int:
    """명령행 인자를 읽고 데이터 로딩부터 리포트 저장까지 실행한다."""

    parser = argparse.ArgumentParser(description="Run Quent MA crossover backtest.")
    parser.add_argument("--config", default="config/strategy.yaml", help="Path to strategy YAML.")
    parser.add_argument("--data", default="data/sample/ohlcv.csv", help="Path to long-format OHLCV CSV.")
    parser.add_argument("--out", default="outputs/example", help="Output directory.")
    args = parser.parse_args()

    # 설정과 데이터는 CLI 인자로 바꿀 수 있어 같은 코드로 여러 실험을 재현할 수 있다.
    config = load_config(args.config)
    data = CsvLongDataLoader().load(args.data)
    # output_dir을 넘기면 BacktestExporter가 전체 산출물을 저장한다.
    result = BacktestEngine(config).run(data, args.out)
    # 콘솔에는 핵심 지표만 간결하게 보여준다.
    print(format_metric_summary(result.metrics))
    print(f"Artifacts: {result.output_dir}")
    return 0


if __name__ == "__main__":
    # main의 반환 코드를 프로세스 종료 코드로 사용한다.
    raise SystemExit(main())
