"""프로젝트 전체에서 공유하는 컬럼명과 기본값 상수."""

# OHLCV 데이터에서 날짜와 종목을 식별하는 표준 컬럼명이다.
DATE_COLUMN = "date"
TICKER_COLUMN = "ticker"
# 전략 실행에 반드시 필요한 최소 OHLCV 컬럼 목록이다.
REQUIRED_OHLCV_COLUMNS = ("date", "ticker", "open", "high", "low", "close", "volume")
# 데이터 소스가 제공하면 사용할 수 있는 선택 컬럼이다.
OPTIONAL_OHLCV_COLUMNS = ("adjusted_close", "dividends", "splits")
# 운영 로그와 run_id 생성에 사용하는 기본 timezone이다.
DEFAULT_TIMEZONE = "Asia/Seoul"
