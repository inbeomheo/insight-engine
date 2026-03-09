"""
SEO 마이그레이션 v2 서비스 — 고급 SEO URL 마이그레이션
"""

import re
import uuid
from dataclasses import dataclass, field


@dataclass
class MigrationRule:
    """마이그레이션 규칙"""
    old_pattern: str
    new_pattern: str
    rule_type: str  # exact / regex / prefix
    priority: int


@dataclass
class MigrationPlan:
    """마이그레이션 계획"""
    plan_id: str
    rules: list[MigrationRule]
    url_count: int
    validated: bool


def create_plan(rules_config: list[dict]) -> MigrationPlan:
    """마이그레이션 계획 생성"""
    rules = []
    for rc in rules_config:
        rule = MigrationRule(
            old_pattern=rc.get('old_pattern', ''),
            new_pattern=rc.get('new_pattern', ''),
            rule_type=rc.get('rule_type', 'exact'),
            priority=rc.get('priority', 0)
        )
        rules.append(rule)

    # 우선순위 내림차순 정렬
    rules.sort(key=lambda r: r.priority, reverse=True)

    return MigrationPlan(
        plan_id=str(uuid.uuid4())[:8],
        rules=rules,
        url_count=0,
        validated=False
    )


def apply_rules(plan: MigrationPlan, urls: list[str]) -> dict[str, str]:
    """URL 매핑 (old → new)"""
    mappings = {}

    for url in urls:
        mapped = url
        for rule in plan.rules:
            if rule.rule_type == 'exact' and url == rule.old_pattern:
                mapped = rule.new_pattern
                break
            elif rule.rule_type == 'prefix' and url.startswith(rule.old_pattern):
                mapped = url.replace(rule.old_pattern, rule.new_pattern, 1)
                break
            elif rule.rule_type == 'regex':
                try:
                    new_url = re.sub(rule.old_pattern, rule.new_pattern, url)
                    if new_url != url:
                        mapped = new_url
                        break
                except re.error:
                    continue

        mappings[url] = mapped

    return mappings


def validate_plan(plan: MigrationPlan) -> list[str]:
    """검증 — 중복 규칙, 순환 리다이렉트"""
    errors = []

    # 중복 old_pattern 체크
    seen_patterns: dict[str, int] = {}
    for rule in plan.rules:
        key = f"{rule.rule_type}:{rule.old_pattern}"
        if key in seen_patterns:
            errors.append(f"중복 규칙: {rule.old_pattern} ({rule.rule_type})")
        seen_patterns[key] = seen_patterns.get(key, 0) + 1

    # 순환 리다이렉트 체크 (exact 규칙만)
    exact_map = {}
    for rule in plan.rules:
        if rule.rule_type == 'exact':
            exact_map[rule.old_pattern] = rule.new_pattern

    for old, new in exact_map.items():
        # A → B → A 순환 체크
        visited = {old}
        current = new
        while current in exact_map:
            if current in visited:
                errors.append(f"순환 리다이렉트 감지: {old} → ... → {current}")
                break
            visited.add(current)
            current = exact_map[current]

    return errors


def generate_htaccess(mappings: dict[str, str]) -> str:
    """.htaccess 리다이렉트 규칙 생성"""
    lines = [
        'RewriteEngine On',
        ''
    ]

    for old, new in mappings.items():
        if old != new:
            # URL 경로 부분만 사용
            lines.append(f'RewriteRule ^{old.lstrip("/")}$ {new} [R=301,L]')

    return '\n'.join(lines)
