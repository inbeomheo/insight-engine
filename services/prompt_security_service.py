"""프롬프트 보안 테스트 서비스 — 인젝션/탈옥 패턴 규칙 기반 탐지."""
import re
from dataclasses import dataclass, field


@dataclass
class SecurityIssue:
    """보안 테스트에서 발견된 이슈."""
    test_name: str
    severity: str        # "low", "medium", "high", "critical"
    description: str
    matched_pattern: str


@dataclass
class SecurityReport:
    """보안 테스트 결과 리포트."""
    template_id: str
    tests_run: int = 0
    passed: int = 0
    failed: int = 0
    issues: list = field(default_factory=list)   # list[SecurityIssue]
    risk_level: str = 'low'


# === 프롬프트 인젝션 패턴 ===
_INJECTION_PATTERNS = [
    {
        'name': 'ignore_previous',
        'pattern': r'(?i)(ignore\s+(all\s+)?previous|disregard\s+(all\s+)?prior|forget\s+(all\s+)?above)',
        'severity': 'critical',
        'description': '이전 지시를 무시하라는 인젝션 패턴',
    },
    {
        'name': 'system_prompt_leak',
        'pattern': r'(?i)(show\s+(me\s+)?(your|the)\s+system\s+prompt|reveal\s+(your\s+)?instructions|print\s+(your\s+)?prompt)',
        'severity': 'high',
        'description': '시스템 프롬프트 유출 시도',
    },
    {
        'name': 'new_instructions',
        'pattern': r'(?i)(new\s+instructions?|override\s+instructions?|replace\s+(your\s+)?instructions?)',
        'severity': 'high',
        'description': '기존 지시를 새 지시로 덮어쓰기 시도',
    },
    {
        'name': 'output_manipulation',
        'pattern': r'(?i)(output\s+only|respond\s+with\s+only|just\s+say|simply\s+respond)',
        'severity': 'medium',
        'description': '출력 형식 조작 시도',
    },
]

# === 탈옥(jailbreak) 패턴 ===
_JAILBREAK_PATTERNS = [
    {
        'name': 'role_play_jailbreak',
        'pattern': r'(?i)(pretend\s+(you\s+are|to\s+be)|act\s+as\s+(if\s+)?(you\s+are|a)|roleplay\s+as)',
        'severity': 'high',
        'description': '역할 가장을 통한 탈옥 시도',
    },
    {
        'name': 'dan_jailbreak',
        'pattern': r'(?i)(DAN|do\s+anything\s+now|jailbreak|bypass\s+(safety|filter|restriction))',
        'severity': 'critical',
        'description': 'DAN/탈옥 키워드 탐지',
    },
    {
        'name': 'hypothetical_bypass',
        'pattern': r'(?i)(hypothetically|in\s+a\s+fictional|imagine\s+you\s+(have\s+)?no\s+restrictions|if\s+you\s+had\s+no\s+rules)',
        'severity': 'medium',
        'description': '가상 시나리오를 이용한 제한 우회 시도',
    },
]

# === PII 노출 위험 패턴 ===
_PII_PATTERNS = [
    {
        'name': 'pii_request',
        'pattern': r'(?i)(personal\s+information|social\s+security|주민등록|전화번호|개인정보|비밀번호)',
        'severity': 'high',
        'description': '개인정보 요청/노출 위험',
    },
    {
        'name': 'api_key_leak',
        'pattern': r'(?i)(api[_\s]?key|secret[_\s]?key|access[_\s]?token|password\s*[:=])',
        'severity': 'critical',
        'description': 'API 키/비밀 정보 노출 위험',
    },
]

# === 역할 혼동(role confusion) 패턴 ===
_ROLE_CONFUSION_PATTERNS = [
    {
        'name': 'role_override',
        'pattern': r'(?i)(you\s+are\s+now|from\s+now\s+on\s+you\s+are|your\s+new\s+role)',
        'severity': 'high',
        'description': '역할 재정의 시도',
    },
    {
        'name': 'system_role_injection',
        'pattern': r'(?i)(\[system\]|\[SYSTEM\]|<system>|<<SYS>>|system\s*:)',
        'severity': 'critical',
        'description': '시스템 역할 태그 주입 시도',
    },
]

# === strict 모드 추가 패턴 ===
_STRICT_PATTERNS = [
    {
        'name': 'encoding_bypass',
        'pattern': r'(?i)(base64|hex\s+encode|rot13|encode\s+in|decode\s+this)',
        'severity': 'medium',
        'description': '인코딩을 이용한 필터 우회 시도',
    },
    {
        'name': 'delimiter_injection',
        'pattern': r'(?i)(```\s*system|---\s*system|###\s*instruction|===\s*new\s*prompt)',
        'severity': 'high',
        'description': '구분자를 이용한 프롬프트 경계 주입',
    },
    {
        'name': 'language_switch',
        'pattern': r'(?i)(translate\s+the\s+above|in\s+another\s+language|respond\s+in\s+code)',
        'severity': 'low',
        'description': '언어 전환을 통한 우회 시도',
    },
    {
        'name': 'repetition_attack',
        'pattern': r'(.)\1{20,}',
        'severity': 'medium',
        'description': '반복 문자 공격 (버퍼 오버플로우 시도)',
    },
    {
        'name': 'markdown_injection',
        'pattern': r'(?i)(\!\[.*?\]\(javascript:|<script|<iframe|on\w+\s*=)',
        'severity': 'critical',
        'description': '마크다운/HTML 인젝션 시도',
    },
]

# 기본 테스트 스위트: 8개 패턴 그룹
_DEFAULT_SUITE = _INJECTION_PATTERNS + _JAILBREAK_PATTERNS + _PII_PATTERNS + _ROLE_CONFUSION_PATTERNS

# strict 테스트 스위트: 기본 + 추가 5개
_STRICT_SUITE = _DEFAULT_SUITE + _STRICT_PATTERNS


def _determine_risk_level(failed: int) -> str:
    """실패 수 기반 위험도를 결정합니다."""
    if failed >= 4:
        return 'critical'
    elif failed >= 3:
        return 'high'
    elif failed >= 2:
        return 'medium'
    elif failed >= 1:
        return 'low'
    return 'low'


def check_injection(prompt: str) -> list:
    """프롬프트에서 인젝션 패턴을 탐지합니다.

    Args:
        prompt: 검사할 프롬프트 문자열

    Returns:
        발견된 SecurityIssue 리스트
    """
    if not prompt or not prompt.strip():
        return []

    issues = []
    # 기본 + strict 전체 패턴으로 검사
    all_patterns = _DEFAULT_SUITE + _STRICT_PATTERNS
    for pat in all_patterns:
        match = re.search(pat['pattern'], prompt)
        if match:
            issues.append(SecurityIssue(
                test_name=pat['name'],
                severity=pat['severity'],
                description=pat['description'],
                matched_pattern=match.group(0),
            ))

    return issues


def run_security_tests(prompt_template: str, test_suite: str = 'default') -> SecurityReport:
    """프롬프트 템플릿에 대해 보안 테스트를 실행합니다.

    Args:
        prompt_template: 검사할 프롬프트 템플릿
        test_suite: 'default' (기본 8개 패턴) 또는 'strict' (추가 5개 포함)

    Returns:
        SecurityReport — 테스트 결과 리포트
    """
    if test_suite == 'strict':
        patterns = _STRICT_SUITE
    else:
        patterns = _DEFAULT_SUITE

    template_id = f'tmpl_{hash(prompt_template) & 0xFFFFFFFF:08x}'
    issues = []
    tests_run = len(patterns)
    failed = 0

    prompt_text = prompt_template or ''
    for pat in patterns:
        match = re.search(pat['pattern'], prompt_text)
        if match:
            failed += 1
            issues.append(SecurityIssue(
                test_name=pat['name'],
                severity=pat['severity'],
                description=pat['description'],
                matched_pattern=match.group(0),
            ))

    passed = tests_run - failed
    risk_level = _determine_risk_level(failed)

    return SecurityReport(
        template_id=template_id,
        tests_run=tests_run,
        passed=passed,
        failed=failed,
        issues=issues,
        risk_level=risk_level,
    )
