"""실행 계층 사용자가 Fill 타입을 한 곳에서 import하게 해주는 모듈."""

from quent.core.types import Fill

# Fill 타입만 공개해 모듈 의도를 분명히 한다.
__all__ = ["Fill"]
