"""성과 차트를 이미지 파일로 생성하는 모듈."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


def save_equity_plot(equity_curve: pd.DataFrame, output_path: str | Path) -> None:
    """equity curve와 drawdown을 하나의 PNG 차트로 저장한다."""

    # 홈 디렉터리 권한 문제를 피하려고 matplotlib 캐시를 /tmp로 둔다.
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/quent-matplotlib")
    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    # equity와 drawdown은 같은 날짜 인덱스를 공유한다.
    equity = equity_curve.set_index("date")["equity"].astype(float)
    drawdown = equity / equity.cummax() - 1.0

    # 위쪽은 자산곡선, 아래쪽은 드로다운으로 배치한다.
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    axes[0].plot(equity.index, equity.values, color="#1f77b4", linewidth=1.8)
    axes[0].set_title("Equity Curve")
    axes[0].set_ylabel("Equity")
    axes[0].grid(True, alpha=0.3)
    axes[1].fill_between(drawdown.index, drawdown.values, 0, color="#d62728", alpha=0.35)
    axes[1].set_title("Drawdown")
    axes[1].set_ylabel("Drawdown")
    axes[1].grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path)
    # 배치 실행에서 figure가 누적되지 않도록 닫는다.
    plt.close(fig)
