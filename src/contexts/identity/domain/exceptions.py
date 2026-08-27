"""Identity & Access BC 도메인 예외.

모든 예외는 `IdentityException`을 상속한다. 호출자(어플리케이션 계층)는
구체 타입을 catch하여 HTTP 응답 코드를 결정할 수 있다.
"""

from __future__ import annotations


class IdentityException(Exception):
    """Identity & Access BC 공통 예외 베이스."""


class AccountNotFound(IdentityException):
    """주어진 AccountId/email로 UserAccount를 찾지 못함."""


class QuotaExceeded(IdentityException):
    """일일 사용량 한도 초과 — 추가 사용 불가."""


class QuotaBackendUnavailable(IdentityException):
    """사용량을 원자적으로 기록할 수 없어 비용 요청을 안전하게 완료할 수 없음."""


class InvalidApiKey(IdentityException):
    """API 키 검증 실패 (만료/형식/소유권 위반 등)."""


class InsufficientCredits(IdentityException):
    """크레딧 잔액 부족 — 결제/충전 필요."""


__all__ = [
    "AccountNotFound",
    "IdentityException",
    "InsufficientCredits",
    "InvalidApiKey",
    "QuotaBackendUnavailable",
    "QuotaExceeded",
]
