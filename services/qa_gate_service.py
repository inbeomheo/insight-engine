"""발행 전 QA 검증 서비스 -- 규칙 기반"""
import re
from config import QA_FORBIDDEN_WORDS, QA_MIN_SECTIONS, QA_MIN_CHARS


def check_quality(content: str, rules: dict = None) -> dict:
    """콘텐츠 품질을 검증합니다.

    Args:
        content: 검사할 콘텐츠
        rules: 커스텀 규칙 (선택)

    Returns:
        {'passed': bool, 'issues': [...], 'score': int}
    """
    issues = []

    # 1. 최소 길이 체크
    if len(content) < QA_MIN_CHARS:
        issues.append({
            'type': 'length',
            'message': f'콘텐츠가 너무 짧습니다 ({len(content)}자 < {QA_MIN_CHARS}자)',
            'severity': 'error',
        })

    # 2. 섹션 수 체크 (마크다운 헤딩)
    sections = re.findall(r'^#{1,3}\s', content, re.MULTILINE)
    if len(sections) < QA_MIN_SECTIONS:
        issues.append({
            'type': 'structure',
            'message': f'섹션이 부족합니다 ({len(sections)}개 < {QA_MIN_SECTIONS}개)',
            'severity': 'warning',
        })

    # 3. 금칙어 체크
    forbidden = rules.get('forbidden_words', QA_FORBIDDEN_WORDS) if rules else QA_FORBIDDEN_WORDS
    found_words = [w for w in forbidden if w in content]
    if found_words:
        issues.append({
            'type': 'forbidden_words',
            'message': f'금칙어 발견: {", ".join(found_words)}',
            'severity': 'warning',
            'words': found_words,
        })

    # 4. 반복 문장 체크
    sentences = [s.strip() for s in re.split(r'[.!?。]\s', content) if len(s.strip()) > 20]
    seen = set()
    duplicates = []
    for s in sentences:
        if s in seen:
            duplicates.append(s[:50])
        seen.add(s)
    if duplicates:
        issues.append({
            'type': 'duplicate',
            'message': f'반복 문장 발견: {len(duplicates)}개',
            'severity': 'warning',
        })

    # 5. 빈 링크/이미지 체크
    broken_links = re.findall(r'\[([^\]]*)\]\(\s*\)', content)
    if broken_links:
        issues.append({
            'type': 'broken_links',
            'message': f'빈 링크 {len(broken_links)}개 발견',
            'severity': 'error',
        })

    errors = [i for i in issues if i['severity'] == 'error']
    passed = len(errors) == 0

    return {'passed': passed, 'issues': issues, 'score': max(0, 100 - len(issues) * 15)}
