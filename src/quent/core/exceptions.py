"""Quent 전용 예외 타입을 모아둔 모듈."""


class QuentError(Exception):
    """프로젝트 전용 예외의 최상위 타입."""


class ConfigError(QuentError):
    """설정 파일 또는 설정값이 유효하지 않을 때 발생한다."""


class DataValidationError(QuentError):
    """시장 데이터가 입력 계약을 위반할 때 발생한다."""


class OrderError(QuentError):
    """주문을 접수하거나 처리할 수 없을 때 발생한다."""


class BrokerError(QuentError):
    """브로커 어댑터에서 인증, 응답 파싱, 네트워크 문제가 생길 때 발생한다."""


class StateStoreError(QuentError):
    """상태 파일 저장 또는 복구에 실패했을 때 발생한다."""
