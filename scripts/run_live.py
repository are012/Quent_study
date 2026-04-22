#!/usr/bin/env python
"""KIS live adapter를 안전한 dry-run 모드로 초기화하는 스크립트."""

from __future__ import annotations

import sys
from pathlib import Path

# 설치 전 로컬 개발 상태에서도 src 패키지를 import할 수 있게 한다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quent.config import load_config
from quent.execution.live_broker_adapter import KisLiveBrokerAdapter


def main() -> int:
    """브로커 설정을 읽고 dry-run 계좌 조회 경로를 확인한다."""

    config = load_config(PROJECT_ROOT / "config" / "strategy.yaml")
    broker = KisLiveBrokerAdapter(config.broker)
    # dry_run을 끈 경우에는 실제 요청 전에 인증 환경변수가 있는지 확인한다.
    if not config.broker.dry_run:
        broker.validate_credentials()
    print({"dry_run": config.broker.dry_run, "account": broker.get_account()})
    return 0


if __name__ == "__main__":
    # main의 반환값을 프로세스 종료 코드로 사용한다.
    raise SystemExit(main())
