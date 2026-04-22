"""백테스트 결과물을 CSV/JSON/YAML/PNG/JSONL 파일로 저장하는 모듈."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from quent.analytics.plots import save_equity_plot
from quent.config import ConfigBundle, config_to_dict
from quent.core.types import BacktestResult


class BacktestExporter:
    """하나의 output_dir 아래에 백테스트 산출물을 저장한다."""

    def __init__(self, output_dir: str | Path) -> None:
        # 출력 디렉터리가 없으면 생성해 CLI 한 번으로 결과를 남길 수 있게 한다.
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        result: BacktestResult,
        config: ConfigBundle,
        event_rows: list[dict[str, object]] | None = None,
    ) -> None:
        """BacktestResult와 설정 스냅샷, 이벤트 로그, 차트를 모두 저장한다."""

        # 시계열/로그성 결과는 사람이 바로 열어볼 수 있도록 CSV로 저장한다.
        _write_csv(result.equity_curve, self.output_dir / "equity_curve.csv")
        _write_csv(result.cash, self.output_dir / "cash.csv")
        _write_csv(result.positions, self.output_dir / "positions.csv")
        _write_csv(result.orders, self.output_dir / "orders.csv")
        _write_csv(result.fills, self.output_dir / "fills.csv")
        _write_csv(result.trades, self.output_dir / "trades.csv")
        # 성과지표는 downstream 도구가 읽기 쉬운 JSON으로 저장한다.
        with (self.output_dir / "metrics.json").open("w", encoding="utf-8") as handle:
            json.dump(_json_safe(result.metrics), handle, indent=2, ensure_ascii=False)
        # 설정 스냅샷은 재현성을 위해 실행 결과와 함께 남긴다.
        with (self.output_dir / "config_snapshot.yaml").open("w", encoding="utf-8") as handle:
            yaml.safe_dump(config_to_dict(config), handle, sort_keys=False, allow_unicode=True)
        # 이벤트 로그는 append/stream 처리에 유리한 JSON lines 형식이다.
        with (self.output_dir / "run.log.jsonl").open("w", encoding="utf-8") as handle:
            for row in event_rows or []:
                handle.write(json.dumps(_json_safe(row), ensure_ascii=False) + "\n")
        if not result.equity_curve.empty:
            # equity curve가 있을 때만 차트 파일을 생성한다.
            save_equity_plot(result.equity_curve, self.output_dir / "tearsheet.png")


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    """빈 DataFrame도 헤더 포함 CSV 파일로 저장한다."""

    if frame.empty:
        frame.to_csv(path, index=False)
        return
    frame.to_csv(path, index=False)


def _json_safe(value):
    """datetime, inf 등 JSON 직렬화가 까다로운 값을 안전하게 변환한다."""

    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if value == float("inf"):
        return "inf"
    return value
