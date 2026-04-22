"""run_id와 로그 타임스탬프를 만들기 위한 시간 헬퍼."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from quent.core.constants import DEFAULT_TIMEZONE


def now_kst() -> datetime:
    """프로젝트 기본 timezone인 Asia/Seoul 현재 시각을 반환한다."""

    return datetime.now(ZoneInfo(DEFAULT_TIMEZONE))


def make_run_id(prefix: str = "run") -> str:
    """정렬 가능한 run_id를 생성한다."""

    # 날짜_시간_마이크로초를 포함해 같은 초에 여러 번 실행해도 충돌 가능성을 줄인다.
    return f"{prefix}_{now_kst().strftime('%Y%m%d_%H%M%S_%f')}"


def iso_now() -> str:
    """현재 시각을 로그 저장에 적합한 ISO 문자열로 반환한다."""

    return now_kst().isoformat()
