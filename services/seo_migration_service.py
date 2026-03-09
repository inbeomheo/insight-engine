"""SEO 마이그레이션 서비스 -- URL 리다이렉트 계획 및 검증"""
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass
class URLMapping:
    """URL 매핑"""
    old_url: str = ""
    new_url: str = ""
    redirect_type: int = 301     # 301 영구, 302 임시
    priority: str = "medium"     # high / medium / low


@dataclass
class MigrationPlan:
    """마이그레이션 계획"""
    mappings: list = field(default_factory=list)  # list[URLMapping]
    total_redirects: int = 0
    risk_level: str = "low"      # low / medium / high / critical


@dataclass
class RedirectIssue:
    """리다이렉트 검증 이슈"""
    old_url: str = ""
    new_url: str = ""
    issue_type: str = ""         # missing_target, chain_redirect, self_redirect, invalid_url
    description: str = ""


def _is_valid_url(url: str) -> bool:
    """URL 형식이 유효한지 검사한다."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def _is_path_only(url: str) -> bool:
    """경로만 있는 상대 URL인지 확인한다."""
    return url.startswith("/") and not url.startswith("//")


def _determine_priority(old_url: str) -> str:
    """URL 패턴으로 우선순위를 결정한다."""
    # 루트 또는 주요 페이지는 높음
    parsed = urlparse(old_url) if _is_valid_url(old_url) else None
    path = parsed.path if parsed else old_url

    # 루트 또는 1단계 경로
    segments = [s for s in path.split("/") if s]
    if len(segments) <= 1:
        return "high"
    # 깊은 경로
    if len(segments) >= 4:
        return "low"
    return "medium"


def _assess_risk(mappings: list[URLMapping]) -> str:
    """매핑 목록으로 리스크 수준을 평가한다."""
    count = len(mappings)
    high_priority = sum(1 for m in mappings if m.priority == "high")

    if count > 100 or high_priority > 20:
        return "critical"
    if count > 50 or high_priority > 10:
        return "high"
    if count > 10 or high_priority > 3:
        return "medium"
    return "low"


def plan_migration(
    old_urls: list[str],
    new_urls: list[str],
) -> MigrationPlan:
    """URL 마이그레이션 계획을 생성한다.

    Args:
        old_urls: 기존 URL 목록
        new_urls: 새 URL 목록 (old_urls와 1:1 대응)

    Returns:
        MigrationPlan
    """
    mappings: list[URLMapping] = []

    # 짧은 쪽에 맞추되 old_urls 기준
    for i, old_url in enumerate(old_urls):
        if not old_url or not old_url.strip():
            continue

        new_url = new_urls[i] if i < len(new_urls) else ""
        if not new_url or not new_url.strip():
            new_url = old_url  # 새 URL 미지정 시 동일 URL

        priority = _determine_priority(old_url)

        mappings.append(URLMapping(
            old_url=old_url.strip(),
            new_url=new_url.strip(),
            redirect_type=301,
            priority=priority,
        ))

    risk_level = _assess_risk(mappings)

    return MigrationPlan(
        mappings=mappings,
        total_redirects=len(mappings),
        risk_level=risk_level,
    )


def validate_redirects(mapping: list[dict]) -> list[RedirectIssue]:
    """리다이렉트 매핑의 유효성을 검증한다.

    Args:
        mapping: [{"old_url": "...", "new_url": "..."}, ...]

    Returns:
        list[RedirectIssue]
    """
    issues: list[RedirectIssue] = []
    new_url_set: set[str] = {m.get("new_url", "") for m in mapping}
    old_url_set: set[str] = {m.get("old_url", "") for m in mapping}

    for entry in mapping:
        old_url = str(entry.get("old_url", ""))
        new_url = str(entry.get("new_url", ""))

        # 셀프 리다이렉트
        if old_url == new_url:
            issues.append(RedirectIssue(
                old_url=old_url,
                new_url=new_url,
                issue_type="self_redirect",
                description="이전 URL과 새 URL이 동일합니다 (무한 루프 위험).",
            ))
            continue

        # URL 형식 검증 (절대 URL이면)
        if old_url.startswith("http"):
            if not _is_valid_url(old_url):
                issues.append(RedirectIssue(
                    old_url=old_url,
                    new_url=new_url,
                    issue_type="invalid_url",
                    description=f"이전 URL 형식이 유효하지 않습니다: {old_url}",
                ))

        if new_url.startswith("http"):
            if not _is_valid_url(new_url):
                issues.append(RedirectIssue(
                    old_url=old_url,
                    new_url=new_url,
                    issue_type="invalid_url",
                    description=f"새 URL 형식이 유효하지 않습니다: {new_url}",
                ))

        # 체인 리다이렉트: new_url이 다른 매핑의 old_url 인 경우
        if new_url in old_url_set and new_url != old_url:
            issues.append(RedirectIssue(
                old_url=old_url,
                new_url=new_url,
                issue_type="chain_redirect",
                description=f"체인 리다이렉트 감지: {old_url} → {new_url} → (다른 리다이렉트)",
            ))

        # 타겟 누락: new_url이 비어있음
        if not new_url.strip():
            issues.append(RedirectIssue(
                old_url=old_url,
                new_url=new_url,
                issue_type="missing_target",
                description="리다이렉트 대상 URL이 지정되지 않았습니다.",
            ))

    return issues
