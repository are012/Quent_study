"""설정 파일을 읽고 타입이 있는 설정 객체로 검증하는 모듈."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from quent.core.exceptions import ConfigError
from quent.core.types import FillModel


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    """전략 파라미터와 초기 자본, sizing 방식을 담는 설정."""

    # 단기/장기 이동평균 창은 신호의 핵심 입력값이다.
    short_window: int = 20
    long_window: int = 60
    # v1은 SMA와 EMA만 명시적으로 지원한다.
    ma_type: str = "sma"
    # 지표 계산에 사용할 가격 컬럼이다.
    price_column: str = "close"
    # True면 adjusted_close를 signal_price로 사용한다.
    use_adjusted: bool = False
    # 백테스트 시작 현금이다.
    initial_capital: float = 10_000_000.0
    # 지정하면 해당 ticker를 buy-and-hold 비교 기준으로 사용한다.
    benchmark: str | None = None
    # fixed_fraction, fixed_notional, equal_weight 중 하나다.
    sizing_method: str = "equal_weight"
    fixed_fraction: float = 0.25
    fixed_notional: float = 2_500_000.0

    def validate(self) -> None:
        """전략 설정이 백테스트를 왜곡하지 않도록 실행 전에 검증한다."""

        if self.short_window <= 0 or self.long_window <= 0:
            raise ConfigError("Moving-average windows must be positive.")
        if self.short_window >= self.long_window:
            raise ConfigError("short_window must be smaller than long_window.")
        if self.ma_type not in {"sma", "ema"}:
            raise ConfigError("ma_type must be 'sma' or 'ema'.")
        if self.initial_capital <= 0:
            raise ConfigError("initial_capital must be positive.")
        if self.sizing_method not in {"fixed_fraction", "fixed_notional", "equal_weight"}:
            raise ConfigError("Unsupported sizing_method.")
        if self.fixed_fraction <= 0:
            raise ConfigError("fixed_fraction must be positive.")
        if self.fixed_notional <= 0:
            raise ConfigError("fixed_notional must be positive.")


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    """체결 모델과 비용 가정을 담는 설정."""

    # 기본은 종가 신호 다음 거래일 시가 체결이다.
    fill_model: FillModel = FillModel.NEXT_OPEN
    # 비율 수수료와 슬리피지는 모든 체결에 적용된다.
    fee_rate: float = 0.00015
    slippage_bps: float = 5.0
    # 최소 수수료와 매도세는 시장별 차이를 설정으로 흡수한다.
    min_fee: float = 0.0
    tax_rate: float = 0.0
    # 너무 작은 주문은 주문 생성 단계에서 차단한다.
    min_order_quantity: int = 1
    min_order_notional: float = 0.0

    def validate(self) -> None:
        """비용/체결 설정의 음수 값과 잘못된 모델을 차단한다."""

        if not isinstance(self.fill_model, FillModel):
            raise ConfigError("fill_model must be a FillModel.")
        for name in ("fee_rate", "slippage_bps", "min_fee", "tax_rate", "min_order_notional"):
            if getattr(self, name) < 0:
                raise ConfigError(f"{name} must be non-negative.")
        if self.min_order_quantity <= 0:
            raise ConfigError("min_order_quantity must be positive.")


@dataclass(frozen=True, slots=True)
class RiskConfig:
    """포트폴리오 단위 리스크 제한 설정."""

    # 기본값은 종목당 25%, 총 노출 100%, 최대 4종목 보유다.
    max_position_weight: float = 0.25
    max_total_exposure: float = 1.0
    max_positions: int = 4
    max_daily_orders: int = 20
    stop_loss_pct: float | None = None
    trailing_stop_pct: float | None = None

    def validate(self) -> None:
        """비중과 주문 제한이 유효한 범위인지 확인한다."""

        if not 0 < self.max_position_weight <= 1:
            raise ConfigError("max_position_weight must be in (0, 1].")
        if not 0 < self.max_total_exposure <= 1:
            raise ConfigError("max_total_exposure must be in (0, 1].")
        if self.max_positions <= 0:
            raise ConfigError("max_positions must be positive.")
        if self.max_daily_orders <= 0:
            raise ConfigError("max_daily_orders must be positive.")
        for name in ("stop_loss_pct", "trailing_stop_pct"):
            value = getattr(self, name)
            if value is not None and not 0 < value < 1:
                raise ConfigError(f"{name} must be None or in (0, 1).")


@dataclass(frozen=True, slots=True)
class BrokerConfig:
    """브로커 어댑터 설정과 인증 환경변수 이름."""

    # v1은 한국투자증권(KIS)과 paper 브로커를 설정 대상으로 둔다.
    name: str = "kis"
    # 안전을 위해 live adapter도 기본 dry-run으로 시작한다.
    dry_run: bool = True
    base_url: str = "https://openapi.koreainvestment.com:9443"
    account_id_env: str = "KIS_ACCOUNT_ID"
    app_key_env: str = "KIS_APP_KEY"
    app_secret_env: str = "KIS_APP_SECRET"
    token_env: str = "KIS_ACCESS_TOKEN"
    timeout_seconds: float = 5.0
    max_retries: int = 3

    def validate(self) -> None:
        """브로커 이름과 네트워크 재시도 설정을 검증한다."""

        if self.name not in {"kis", "paper"}:
            raise ConfigError("broker name must be 'kis' or 'paper'.")
        if self.timeout_seconds <= 0:
            raise ConfigError("timeout_seconds must be positive.")
        if self.max_retries < 0:
            raise ConfigError("max_retries must be non-negative.")


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    """로그 레벨과 JSON lines 사용 여부."""

    level: str = "INFO"
    json_lines: bool = True

    def validate(self) -> None:
        """운영 로그 레벨이 표준 값인지 확인한다."""

        if self.level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigError("Invalid logging level.")


@dataclass(frozen=True, slots=True)
class ConfigBundle:
    """전략, 체결, 리스크, 브로커, 로그 설정을 한 번에 묶은 객체."""

    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    broker: BrokerConfig = field(default_factory=BrokerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def validate(self) -> None:
        """하위 설정 객체를 모두 검증한다."""

        self.strategy.validate()
        self.execution.validate()
        self.risk.validate()
        self.broker.validate()
        self.logging.validate()


def _read_yaml(path: Path) -> dict[str, Any]:
    """YAML 파일이 없으면 빈 설정으로 간주하고, 있으면 mapping으로 읽는다."""

    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ConfigError(f"{path} must contain a YAML mapping.")
    return loaded


def _coerce_fill_model(value: Any) -> FillModel:
    """문자열 설정값을 FillModel enum으로 변환한다."""

    try:
        return value if isinstance(value, FillModel) else FillModel(str(value))
    except ValueError as exc:
        raise ConfigError("fill_model must be 'next_open' or 'next_close'.") from exc


def load_config(strategy_path: str | Path) -> ConfigBundle:
    """전략 설정 파일과 같은 디렉터리의 보조 설정 파일을 함께 읽는다."""

    # strategy.yaml을 기준으로 execution/risk/broker/logging 파일을 찾는다.
    strategy_path = Path(strategy_path)
    config_dir = strategy_path.parent

    # 각 파일은 비어 있거나 없어도 dataclass 기본값으로 보완된다.
    strategy_data = _read_yaml(strategy_path)
    execution_data = _read_yaml(config_dir / "execution.yaml")
    risk_data = _read_yaml(config_dir / "risk.yaml")
    broker_data = _read_yaml(config_dir / "broker.yaml")
    logging_data = _read_yaml(config_dir / "logging.yaml")

    # YAML에서는 enum을 문자열로 쓰므로 객체 생성 전에 변환한다.
    if "fill_model" in execution_data:
        execution_data["fill_model"] = _coerce_fill_model(execution_data["fill_model"])

    # dataclass 생성 시 알 수 없는 키가 있으면 TypeError가 나서 설정 오류를 빨리 발견한다.
    bundle = ConfigBundle(
        strategy=StrategyConfig(**strategy_data),
        execution=ExecutionConfig(**execution_data),
        risk=RiskConfig(**risk_data),
        broker=BrokerConfig(**broker_data),
        logging=LoggingConfig(**logging_data),
    )
    # 모든 설정 검증을 통과해야 실행 계층으로 넘어간다.
    bundle.validate()
    return bundle


def config_to_dict(config: ConfigBundle) -> dict[str, Any]:
    """ConfigBundle을 결과물 저장에 적합한 YAML 직렬화 형태로 바꾼다."""

    # FillModel enum은 YAML/JSON에 안전한 문자열 값으로 저장한다.
    return {
        "strategy": asdict(config.strategy),
        "execution": {
            **asdict(config.execution),
            "fill_model": config.execution.fill_model.value,
        },
        "risk": asdict(config.risk),
        "broker": asdict(config.broker),
        "logging": asdict(config.logging),
    }
