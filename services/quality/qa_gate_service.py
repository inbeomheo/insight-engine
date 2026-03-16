"""발행 전 QA 검증 서비스 -- 규칙 기반"""
import logging
import re
from config import QA_FORBIDDEN_WORDS, QA_MIN_SECTIONS, QA_MIN_CHARS


logger = logging.getLogger(__name__)

def _check_length(content: str) -> list:
    """최소 길이를 검사합니다."""
    if len(content) < QA_MIN_CHARS:
        return [{'type': 'length', 'severity': 'error',
                 'message': f'콘텐츠가 너무 짧습니다 ({len(content)}자 < {QA_MIN_CHARS}자)'}]
    return []


def _check_sections(content: str) -> list:
    """마크다운 헤딩 기반 섹션 수를 검사합니다."""
    sections = re.findall(r'^#{1,3}\s', content, re.MULTILINE)
    if len(sections) < QA_MIN_SECTIONS:
        return [{'type': 'structure', 'severity': 'warning',
                 'message': f'섹션이 부족합니다 ({len(sections)}개 < {QA_MIN_SECTIONS}개)'}]
    return []


def _check_forbidden_words(content: str, rules: dict = None) -> list:
    """금칙어 포함 여부를 검사합니다."""
    forbidden = rules.get('forbidden_words', QA_FORBIDDEN_WORDS) if rules else QA_FORBIDDEN_WORDS
    found = [w for w in forbidden if w in content]
    if found:
        return [{'type': 'forbidden_words', 'severity': 'warning',
                 'message': f'금칙어 발견: {", ".join(found)}', 'words': found}]
    return []


def _check_duplicates(content: str) -> list:
    """반복 문장을 검사합니다."""
    sentences = [s.strip() for s in re.split(r'[.!?。]\s', content) if len(s.strip()) > 20]
    seen = set()
    duplicates = []
    for s in sentences:
        if s in seen:
            duplicates.append(s[:50])
        seen.add(s)
    if duplicates:
        return [{'type': 'duplicate', 'severity': 'warning',
                 'message': f'반복 문장 발견: {len(duplicates)}개'}]
    return []


def _check_broken_links(content: str) -> list:
    """빈 링크/이미지를 검사합니다."""
    broken = re.findall(r'\[([^\]]*)\]\(\s*\)', content)
    if broken:
        return [{'type': 'broken_links', 'severity': 'error',
                 'message': f'빈 링크 {len(broken)}개 발견'}]
    return []


_SUGGESTION_MAP = {
    'length': '콘텐츠를 보강하여 최소 글자 수 기준을 충족해 주세요.',
    'structure': '## 또는 ### 헤딩을 추가하여 글의 구조를 개선해 주세요.',
    'forbidden_words': '금칙어를 동의어 또는 구체적 표현으로 교체해 주세요.',
    'duplicate': '반복되는 문장을 제거하거나 다른 표현으로 다듬어 주세요.',
    'broken_links': '빈 링크의 URL을 채우거나 해당 링크를 제거해 주세요.',
}


def _build_suggestions(issues: list) -> list:
    """이슈 목록에서 최대 3개의 개선 제안 문구를 생성합니다."""
    seen = set()
    suggestions = []
    for issue in issues:
        t = issue.get('type', '')
        if t not in seen and t in _SUGGESTION_MAP:
            seen.add(t)
            suggestions.append(_SUGGESTION_MAP[t])
        if len(suggestions) >= 3:
            break
    return suggestions


def check_quality(content: str, rules: dict = None) -> dict:
    """콘텐츠 품질을 검증합니다.

    Args:
        content: 검사할 콘텐츠
        rules: 커스텀 규칙 (선택)

    Returns:
        {'passed': bool, 'issues': [...], 'score': int}
    """
    try:
        issues = (
            _check_length(content)
            + _check_sections(content)
            + _check_forbidden_words(content, rules)
            + _check_duplicates(content)
            + _check_broken_links(content)
        )

        errors = [i for i in issues if i['severity'] == 'error']
        warnings = [i for i in issues if i['severity'] == 'warning']
        penalty = len(errors) * 25 + len(warnings) * 10
        score = max(0, 100 - penalty)
        suggestions = _build_suggestions(issues)
        return {
            'passed': len(errors) == 0,
            'issues': issues,
            'score': score,
            'error_count': len(errors),
            'warning_count': len(warnings),
            'suggestions': suggestions,
        }
    except Exception as e:
        logger.error(f"QA 검증 처리 실패: {e}")
        return {'passed': False, 'issues': [], 'score': 0}
