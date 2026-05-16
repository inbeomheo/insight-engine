"""
콘텐츠 비교(Diff) 서비스

두 콘텐츠 버전을 비교하여 추가/삭제/변경 부분을 분석합니다.
difflib 기반 규칙 처리로 AI 호출 없이 즉시 결과 반환.
"""
import difflib
import logging
import re
from typing import List

logger = logging.getLogger(__name__)


def _split_into_lines(text: str) -> List[str]:
    """텍스트를 줄 단위로 분리합니다."""
    return text.splitlines(keepends=True)


def _word_count(text: str) -> int:
    """단어 수를 반환합니다 (한국어: 형태소 근사, 영어: 공백 분리)."""
    # 한국어+영어 혼합 지원
    words = re.findall(r'[\w가-힣]+', text)
    return len(words)


def compare_content(original: str, revised: str) -> dict:
    """두 콘텐츠 버전을 비교합니다.

    Args:
        original: 원본 콘텐츠
        revised: 수정된 콘텐츠

    Returns:
        {
            'similarity': float (0.0~1.0),
            'changes': [{'type': 'add'|'delete'|'replace', 'original': str, 'revised': str, 'line': int}],
            'stats': {'additions': int, 'deletions': int, 'modifications': int, 'unchanged': int},
            'word_diff': {'original': int, 'revised': int, 'delta': int},
            'char_diff': {'original': int, 'revised': int, 'delta': int},
        }
    """
    if original is None:
        original = ''
    if revised is None:
        revised = ''

    orig_lines = _split_into_lines(original)
    rev_lines = _split_into_lines(revised)

    # 유사도 계산
    matcher = difflib.SequenceMatcher(None, original, revised)
    similarity = round(matcher.ratio(), 4)

    # 줄 단위 diff
    changes = []
    stats = {'additions': 0, 'deletions': 0, 'modifications': 0, 'unchanged': 0}

    opcodes = difflib.SequenceMatcher(None, orig_lines, rev_lines).get_opcodes()
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'equal':
            stats['unchanged'] += i2 - i1
        elif tag == 'insert':
            for j in range(j1, j2):
                changes.append({
                    'type': 'add',
                    'original': '',
                    'revised': rev_lines[j].rstrip('\n'),
                    'line': j + 1,
                })
            stats['additions'] += j2 - j1
        elif tag == 'delete':
            for i in range(i1, i2):
                changes.append({
                    'type': 'delete',
                    'original': orig_lines[i].rstrip('\n'),
                    'revised': '',
                    'line': i + 1,
                })
            stats['deletions'] += i2 - i1
        elif tag == 'replace':
            max_len = max(i2 - i1, j2 - j1)
            for k in range(max_len):
                orig_text = orig_lines[i1 + k].rstrip('\n') if i1 + k < i2 else ''
                rev_text = rev_lines[j1 + k].rstrip('\n') if j1 + k < j2 else ''
                changes.append({
                    'type': 'replace',
                    'original': orig_text,
                    'revised': rev_text,
                    'line': (i1 + k + 1) if i1 + k < i2 else (j1 + k + 1),
                })
            stats['modifications'] += max_len

    # 단어/글자 수 비교
    orig_words = _word_count(original)
    rev_words = _word_count(revised)

    return {
        'similarity': similarity,
        'changes': changes,
        'stats': stats,
        'word_diff': {
            'original': orig_words,
            'revised': rev_words,
            'delta': rev_words - orig_words,
        },
        'char_diff': {
            'original': len(original),
            'revised': len(revised),
            'delta': len(revised) - len(original),
        },
    }


def generate_unified_diff(original: str, revised: str,
                          label_a: str = '원본', label_b: str = '수정본',
                          context_lines: int = 3) -> str:
    """Unified diff 형식의 텍스트를 생성합니다.

    Args:
        original: 원본 텍스트
        revised: 수정 텍스트
        label_a: 원본 라벨
        label_b: 수정본 라벨
        context_lines: 컨텍스트 줄 수

    Returns:
        unified diff 문자열
    """
    if original is None:
        original = ''
    if revised is None:
        revised = ''

    orig_lines = _split_into_lines(original)
    rev_lines = _split_into_lines(revised)

    diff = difflib.unified_diff(
        orig_lines, rev_lines,
        fromfile=label_a, tofile=label_b,
        lineterm='',
        n=context_lines,
    )
    return '\n'.join(line.rstrip('\n') for line in diff)
