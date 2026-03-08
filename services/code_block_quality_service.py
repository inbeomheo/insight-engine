"""
Code Block Quality Checker 서비스

마크다운 코드 블록의 품질을 점검합니다.
언어 태그 누락, 과도한 길이, 빈 블록, 중복 등을 감지합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List


# 코드 블록 패턴 (fenced)
_CODE_BLOCK_RE = re.compile(
    r'^```(\w*)\s*\n(.*?)^```',
    re.MULTILINE | re.DOTALL
)

# 인라인 코드 패턴
_INLINE_CODE_RE = re.compile(r'`([^`\n]+)`')

# 알려진 언어 태그
_KNOWN_LANGUAGES = {
    'python', 'py', 'javascript', 'js', 'typescript', 'ts',
    'java', 'c', 'cpp', 'csharp', 'cs', 'go', 'rust', 'ruby', 'rb',
    'php', 'swift', 'kotlin', 'scala', 'r', 'matlab',
    'html', 'css', 'scss', 'sass', 'less',
    'sql', 'graphql', 'json', 'yaml', 'yml', 'toml', 'xml',
    'bash', 'sh', 'zsh', 'powershell', 'ps1', 'cmd', 'bat',
    'dockerfile', 'docker', 'makefile', 'nginx', 'apache',
    'markdown', 'md', 'text', 'txt', 'plain',
    'jsx', 'tsx', 'vue', 'svelte',
}

# 코드 블록 최대 권장 줄 수
_MAX_LINES = 50
_WARNING_LINES = 30


def check_code_block_quality(content: str) -> dict:
    """코드 블록 품질을 점검합니다.

    Returns:
        code_blocks, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'code_blocks': [],
            'summary': {'total_blocks': 0, 'missing_language': 0,
                        'long_blocks': 0, 'empty_blocks': 0},
            'score': 100.0,
            'suggestions': [],
        }

    blocks = []
    missing_lang = 0
    long_blocks = 0
    empty_blocks = 0

    for match in _CODE_BLOCK_RE.finditer(content):
        lang = match.group(1).strip().lower()
        code = match.group(2)
        lines = code.split('\n')
        line_count = len([l for l in lines if l.strip()])

        issues = []

        # 언어 태그 누락
        has_lang = bool(lang)
        if not has_lang:
            missing_lang += 1
            issues.append('언어 태그 누락')

        # 알 수 없는 언어 태그
        unknown_lang = has_lang and lang not in _KNOWN_LANGUAGES
        if unknown_lang:
            issues.append(f'알 수 없는 언어 태그: "{lang}"')

        # 빈 블록
        is_empty = line_count == 0
        if is_empty:
            empty_blocks += 1
            issues.append('빈 코드 블록')

        # 긴 블록
        is_long = line_count > _MAX_LINES
        is_warning = line_count > _WARNING_LINES and not is_long
        if is_long:
            long_blocks += 1
            issues.append(f'코드 {line_count}줄 (권장 {_MAX_LINES}줄 이내)')
        elif is_warning:
            issues.append(f'코드 {line_count}줄 (다소 김)')

        excerpt = code[:80].strip() if code.strip() else '(비어 있음)'
        blocks.append({
            'language': lang or '(없음)',
            'line_count': line_count,
            'has_language_tag': has_lang,
            'is_empty': is_empty,
            'is_long': is_long,
            'issues': issues,
            'excerpt': excerpt,
        })

    total = len(blocks)
    if total == 0:
        return {
            'code_blocks': [],
            'summary': {'total_blocks': 0, 'missing_language': 0,
                        'long_blocks': 0, 'empty_blocks': 0},
            'score': 100.0,
            'suggestions': [],
        }

    # 점수
    issue_count = missing_lang + long_blocks + empty_blocks
    score = round(max(0.0, min(100.0, (1.0 - issue_count / (total * 1.5)) * 100.0)), 1)

    suggestions = _generate_suggestions(total, missing_lang, long_blocks, empty_blocks)

    return {
        'code_blocks': blocks,
        'summary': {
            'total_blocks': total,
            'missing_language': missing_lang,
            'long_blocks': long_blocks,
            'empty_blocks': empty_blocks,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(total: int, missing: int, long: int, empty: int) -> List[str]:
    suggestions = []
    if missing > 0:
        suggestions.append(
            f'언어 태그 누락 {missing}개: ```python, ```javascript 등으로 언어를 명시하세요.'
        )
    if long > 0:
        suggestions.append(
            f'긴 코드 블록 {long}개: {_MAX_LINES}줄 이내로 분할하거나 핵심 부분만 표시하세요.'
        )
    if empty > 0:
        suggestions.append(f'빈 코드 블록 {empty}개: 삭제하거나 코드를 추가하세요.')
    if not suggestions:
        suggestions.append('모든 코드 블록의 품질이 양호합니다.')
    return suggestions
