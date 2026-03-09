"""
샌드박스 데모 서비스 — 제한된 환경에서 API 체험
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class SandboxConfig:
    """샌드박스 설정"""
    sandbox_id: str
    allowed_endpoints: list  # ["/api/generate", "/api/styles"]
    rate_limit: int  # 분당 요청 수
    ttl_minutes: int  # 유효 시간 (분)
    created_at: str  # ISO 8601


@dataclass
class SandboxSession:
    """샌드박스 세션"""
    session_id: str
    config: SandboxConfig
    request_count: int = 0
    is_expired: bool = False


def create_sandbox(endpoints: list, rate_limit: int = 10, ttl: int = 30) -> SandboxSession:
    """샌드박스 세션 생성"""
    if not endpoints:
        raise ValueError("허용 엔드포인트가 최소 1개 필요합니다")
    if rate_limit <= 0:
        raise ValueError("rate_limit은 1 이상이어야 합니다")
    if ttl <= 0:
        raise ValueError("TTL은 1분 이상이어야 합니다")

    config = SandboxConfig(
        sandbox_id=str(uuid.uuid4()),
        allowed_endpoints=endpoints,
        rate_limit=rate_limit,
        ttl_minutes=ttl,
        created_at=datetime.now().isoformat(),
    )

    return SandboxSession(
        session_id=str(uuid.uuid4()),
        config=config,
    )


def validate_request(session: SandboxSession, endpoint: str, current_time: str = "") -> dict:
    """요청 유효성 검사"""
    # 만료 체크
    if current_time:
        try:
            created = datetime.fromisoformat(session.config.created_at)
            now = datetime.fromisoformat(current_time)
            elapsed = (now - created).total_seconds() / 60
            if elapsed > session.config.ttl_minutes:
                session.is_expired = True
        except (ValueError, TypeError):
            pass

    if session.is_expired:
        return {
            "allowed": False,
            "reason": "세션 만료",
            "session_id": session.session_id,
        }

    # 엔드포인트 체크
    if endpoint not in session.config.allowed_endpoints:
        return {
            "allowed": False,
            "reason": f"허용되지 않은 엔드포인트: {endpoint}",
            "session_id": session.session_id,
        }

    # 속도 제한 체크
    if session.request_count >= session.config.rate_limit:
        return {
            "allowed": False,
            "reason": "속도 제한 초과",
            "session_id": session.session_id,
        }

    # 허용
    session.request_count += 1
    return {
        "allowed": True,
        "reason": "허용",
        "session_id": session.session_id,
        "remaining": session.config.rate_limit - session.request_count,
    }


def get_usage_stats(session: SandboxSession) -> dict:
    """사용량 통계"""
    return {
        "session_id": session.session_id,
        "sandbox_id": session.config.sandbox_id,
        "request_count": session.request_count,
        "rate_limit": session.config.rate_limit,
        "remaining": max(0, session.config.rate_limit - session.request_count),
        "ttl_minutes": session.config.ttl_minutes,
        "is_expired": session.is_expired,
        "allowed_endpoints": session.config.allowed_endpoints,
    }
