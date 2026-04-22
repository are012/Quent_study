# Quent

Quent는 **일봉 이동평균 추세추종 전략**을 연구, 검증, 리포팅, 페이퍼 실행까지 연결하기 위한 Python 프로젝트입니다.  
단순 예제 코드가 아니라, 신호 시점과 체결 시점을 분리하고 거래비용, 슬리피지, 리스크 제한, 결과 저장, 브로커 추상화를 포함하는 재현 가능한 자동매매 기반 시스템을 목표로 합니다.

## 핵심 기능

- CSV long format OHLCV 데이터 로딩
- 데이터 정렬, 중복, 결측, 음수 가격/거래량, OHLC 논리 검증
- SMA/EMA 이동평균 계산
- 이동평균 교차 기반 롱 온리 신호 생성
- 종가 기준 신호 계산 후 다음 거래일 시가 체결
- 수수료, 슬리피지, 매도세 옵션 반영
- fixed fraction, fixed notional, equal weight 포지션 sizing
- 종목당 최대 비중, 총 노출, 최대 보유 종목 수, 일일 주문 수 제한
- 단일 종목 및 다종목 백테스트
- 성과지표, CSV/JSON/YAML/PNG/JSONL 결과 저장
- Paper broker와 한국투자증권 KIS live adapter 골격
- pytest 기반 단위/통합/회귀 테스트

## 프로젝트 구조

```text
config/                 실행 설정 샘플
data/sample/            샘플 OHLCV CSV
docs/                   전략, 아키텍처, 운영, 가정 문서
scripts/                CLI 실행 스크립트
src/quent/              실제 Python 패키지
tests/                  단위, 통합, 회귀 테스트
outputs/                실행 결과물 생성 위치
```

주요 패키지 책임은 다음과 같습니다.

- `quent.data`: CSV 로딩과 데이터 검증
- `quent.indicators`: SMA/EMA 계산
- `quent.signals`: 이동평균 교차 신호 생성
- `quent.portfolio`: 현금, 포지션, sizing, 리스크 제한
- `quent.backtest`: 순차형 일봉 백테스트 엔진과 체결 시뮬레이터
- `quent.analytics`: 성과지표와 차트
- `quent.reporting`: 결과 파일 저장
- `quent.execution`: Paper broker와 KIS live adapter
- `quent.storage`: 상태 저장, 거래 로그, run registry

## 설치

Python 3.13 이상을 기준으로 합니다.

```bash
python -m pip install -e ".[test]"
```

## 테스트

```bash
python -m pytest
```

현재 기대 결과:

```text
13 passed
```

테스트는 이동평균 계산, 신호 지연, 비용 계산, 리스크 제한, 성과지표, 브로커 dry-run, 샘플 백테스트 회귀값을 검증합니다.

## 샘플 백테스트 실행

```bash
python scripts/run_backtest.py \
  --config config/strategy.yaml \
  --data data/sample/ohlcv.csv \
  --out outputs/example
```

예상 콘솔 출력:

```text
Backtest Summary
final_equity: 10954895.214775262
total_return: 0.0954895214775262
cagr: 2.4340870845517775
max_drawdown: 0.0
sharpe: 27.084311154945652
trade_count: 0
profit_factor: 0.0
buy_hold_return: 0.5588235294117649
Artifacts: outputs/example
```

샘플 데이터는 매우 짧고 인위적이므로 CAGR과 Sharpe는 투자 판단용 수치가 아니라 파이프라인 검증용 결과로 보아야 합니다.

## 생성 결과물

백테스트를 실행하면 `outputs/example/` 아래에 다음 파일이 생성됩니다.

```text
cash.csv
config_snapshot.yaml
equity_curve.csv
fills.csv
metrics.json
orders.csv
positions.csv
run.log.jsonl
tearsheet.png
trades.csv
```

각 파일의 의미:

- `equity_curve.csv`: 일별 총자산, 포지션 평가금액, 시장 노출도
- `cash.csv`: 일별 현금과 현금 비중
- `positions.csv`: 일별 보유 포지션 스냅샷
- `orders.csv`: 생성된 주문 로그
- `fills.csv`: 체결 로그, 체결가, 수수료, 세금, 슬리피지
- `trades.csv`: 청산 완료된 거래 손익 로그
- `metrics.json`: 누적수익률, CAGR, MDD, Sharpe, Sortino, turnover 등 성과지표
- `config_snapshot.yaml`: 실행 당시 설정값 스냅샷
- `run.log.jsonl`: 감사 추적용 이벤트 로그
- `tearsheet.png`: equity curve와 drawdown 차트

## 데이터 형식

기본 입력은 CSV long format입니다.

```text
date,ticker,open,high,low,close,volume
2024-01-02,AAA,10.0,10.4,9.8,10.2,100000
```

필수 컬럼:

- `date`
- `ticker`
- `open`
- `high`
- `low`
- `close`
- `volume`

선택 컬럼:

- `adjusted_close`
- `dividends`
- `splits`

날짜는 timezone-naive 일자 단위로 정규화됩니다. 조정가격을 쓰려면 `config/strategy.yaml`에서 `use_adjusted: true`로 설정하고 `adjusted_close` 컬럼을 제공해야 합니다.

## 기본 전략 규칙

- 기본 전략은 롱 온리입니다.
- `short_ma > long_ma`이면 raw long regime입니다.
- `short_ma <= long_ma`이면 raw flat regime입니다.
- raw signal은 당일 종가가 확정된 뒤 계산됩니다.
- executable signal은 종목별 raw signal을 한 거래일 지연한 값입니다.
- 기본 체결 모델은 다음 거래일 시가입니다.
- 이미 보유 중인 종목에는 반복 매수하지 않습니다.
- executable signal이 false로 바뀌면 해당 종목 전체 수량을 매도합니다.

## 기본 설정

`config/strategy.yaml`

- `short_window: 3`
- `long_window: 5`
- `ma_type: sma`
- `initial_capital: 10000000`
- `sizing_method: equal_weight`

`config/execution.yaml`

- `fill_model: next_open`
- `fee_rate: 0.00015`
- `slippage_bps: 5`
- `tax_rate: 0`

`config/risk.yaml`

- `max_position_weight: 0.25`
- `max_total_exposure: 1.0`
- `max_positions: 4`
- `max_daily_orders: 20`

## Paper / Live 실행 확인

페이퍼 브로커 확인:

```bash
python scripts/run_paper.py
```

예상 출력:

```text
BrokerAccount(cash=10000000.0, equity=10000000.0, buying_power=10000000.0, currency='KRW')
```

한국투자증권 KIS adapter dry-run 확인:

```bash
python scripts/run_live.py
```

예상 출력:

```text
{'dry_run': True, 'account': BrokerAccount(cash=0.0, equity=0.0, buying_power=0.0, currency='KRW')}
```

`config/broker.yaml`의 기본값은 `dry_run: true`입니다. 실제 주문을 보내려면 KIS 인증 환경변수와 실제 transport 구현, 상태 동기화 검증이 필요합니다.

## 운영 주의사항

- 이 프로젝트는 투자 조언이나 수익 보장을 제공하지 않습니다.
- 백테스트 결과는 데이터 품질, 비용 가정, 체결 가정에 크게 의존합니다.
- 실거래 전에는 반드시 paper 모드, 소액 검증, 브로커 상태 동기화, 주문 제한 설정을 확인해야 합니다.
- `outputs/`는 실행 결과물이므로 기본적으로 git 추적에서 제외됩니다.

자세한 설계와 운영 절차는 다음 문서를 참고하세요.

- `docs/strategy_spec.md`
- `docs/architecture.md`
- `docs/operations.md`
- `docs/assumptions.md`
