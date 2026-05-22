"""Identity & Access 도메인 계층 — 엔티티, 값 객체, 도메인 이벤트, 예외.

이 패키지는 외부 의존성이 없는 순수 도메인 모델만 보관한다.
DB, HTTP, Flask 등 인프라 관심사는 절대 import하지 않는다.
"""

from src.contexts.identity.domain.events import (
    AccountCreated,
    ApiKeyAdded,
    DomainEvent,
    QuotaConsumed,
)
from src.contexts.identity.domain.exceptions import (
    AccountNotFound,
    IdentityException,
    InsufficientCredits,
    InvalidApiKey,
    QuotaExceeded,
)
from src.contexts.identity.domain.user_account import (
    ApiKey,
    CreditBalance,
    RbacRole,
    UsageQuota,
    UserAccount,
)

__all__ = [
    # Aggregate + entities
    "ApiKey",
    "CreditBalance",
    "RbacRole",
    "UsageQuota",
    "UserAccount",
    # Domain events
    "AccountCreated",
    "ApiKeyAdded",
    "DomainEvent",
    "QuotaConsumed",
    # Exceptions
    "AccountNotFound",
    "IdentityException",
    "InsufficientCredits",
    "InvalidApiKey",
    "QuotaExceeded",
]
