"""
AI 크롤링 게이트웨이 서비스 — AI 크롤러 접근 제어
"""

import uuid
from dataclasses import dataclass, field
from fnmatch import fnmatch


@dataclass
class CrawlRule:
    """크롤링 규칙"""
    rule_id: str
    bot_name: str
    allowed_paths: list  # ["/public/*", "/api/docs"]
    blocked_paths: list  # ["/admin/*", "/internal/*"]
    rate_limit: int  # 분당 요청 수


@dataclass
class CrawlDecision:
    """크롤링 결정"""
    bot_name: str
    path: str
    allowed: bool
    reason: str


def evaluate_request(bot_name: str, path: str, rules: list) -> CrawlDecision:
    """접근 허용 여부 판단"""
    # 봇에 해당하는 규칙 찾기
    matching_rules = [r for r in rules if r.bot_name == bot_name or r.bot_name == "*"]

    if not matching_rules:
        # 규칙 없으면 기본 거부
        return CrawlDecision(
            bot_name=bot_name,
            path=path,
            allowed=False,
            reason="해당 봇에 대한 규칙이 없음",
        )

    for rule in matching_rules:
        # 차단 경로 우선 확인
        for blocked in rule.blocked_paths:
            if fnmatch(path, blocked):
                return CrawlDecision(
                    bot_name=bot_name,
                    path=path,
                    allowed=False,
                    reason=f"차단 경로 매칭: {blocked}",
                )

        # 허용 경로 확인
        for allowed in rule.allowed_paths:
            if fnmatch(path, allowed):
                return CrawlDecision(
                    bot_name=bot_name,
                    path=path,
                    allowed=True,
                    reason=f"허용 경로 매칭: {allowed}",
                )

    return CrawlDecision(
        bot_name=bot_name,
        path=path,
        allowed=False,
        reason="허용 경로에 매칭되지 않음",
    )


def generate_robots_txt(rules: list) -> str:
    """robots.txt 생성"""
    lines = []
    for rule in rules:
        lines.append(f"User-agent: {rule.bot_name}")
        for path in rule.allowed_paths:
            lines.append(f"Allow: {path}")
        for path in rule.blocked_paths:
            lines.append(f"Disallow: {path}")
        if rule.rate_limit > 0:
            # Crawl-delay = 60 / rate_limit (초 단위)
            delay = max(1, 60 // rule.rate_limit)
            lines.append(f"Crawl-delay: {delay}")
        lines.append("")  # 빈 줄 구분

    return "\n".join(lines)


def check_rate_limit(bot_name: str, request_count: int, rules: list) -> bool:
    """속도 제한 체크 — True면 허용, False면 초과"""
    for rule in rules:
        if rule.bot_name == bot_name or rule.bot_name == "*":
            return request_count <= rule.rate_limit
    # 규칙 없으면 기본 거부
    return False


def get_bot_stats(decisions: list) -> dict:
    """봇별 접근 통계"""
    stats = {}
    for d in decisions:
        if d.bot_name not in stats:
            stats[d.bot_name] = {"total": 0, "allowed": 0, "blocked": 0}
        stats[d.bot_name]["total"] += 1
        if d.allowed:
            stats[d.bot_name]["allowed"] += 1
        else:
            stats[d.bot_name]["blocked"] += 1

    return stats
