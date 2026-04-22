"""CLI에 보여줄 간단한 성과 요약 문자열을 만드는 헬퍼."""

from __future__ import annotations


def format_metric_summary(metrics: dict[str, object]) -> str:
    """핵심 지표만 골라 콘솔 출력용 텍스트로 포맷한다."""

    # 너무 많은 지표를 콘솔에 쏟지 않고 실행 확인에 필요한 값만 보여준다.
    keys = [
        "final_equity",
        "total_return",
        "cagr",
        "max_drawdown",
        "sharpe",
        "trade_count",
        "profit_factor",
        "buy_hold_return",
    ]
    lines = ["Backtest Summary"]
    for key in keys:
        # 계산되지 않은 지표는 출력하지 않는다.
        if key in metrics:
            lines.append(f"{key}: {metrics[key]}")
    return "\n".join(lines)
