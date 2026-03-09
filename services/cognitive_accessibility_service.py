"""
인지 접근성 서비스

다양한 인지적 요구(난독증, ADHD, 저시력 등)에 맞춰
콘텐츠를 변환하는 프리셋을 제공합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class CognitivePreset:
    """인지 접근성 프리셋 정의."""
    name: str
    description: str
    rules: List[str] = field(default_factory=list)


# 프리셋 정의
_PRESETS = {
    'general': CognitivePreset(
        name='general',
        description='모든 사용자를 위한 기본 접근성 개선',
        rules=[
            '긴 문단을 3문장 이내로 분리',
            '약어를 처음 사용 시 풀어쓰기',
        ],
    ),
    'dyslexia': CognitivePreset(
        name='dyslexia',
        description='난독증 사용자를 위한 최적화 (단어 간격, 약어 풀어쓰기)',
        rules=[
            '긴 문단을 3문장 이내로 분리',
            '약어를 처음 사용 시 풀어쓰기',
            '긴 복합어에 가운뎃점(·) 삽입',
            '괄호 내 약어를 풀어서 표기',
        ],
    ),
    'adhd': CognitivePreset(
        name='adhd',
        description='주의력 결핍 사용자를 위한 최적화 (짧은 문단, 핵심 강조)',
        rules=[
            '긴 문단을 3문장 이내로 분리',
            '약어를 처음 사용 시 풀어쓰기',
            '각 문단의 첫 문장을 핵심 포인트로 볼드 처리',
            '문단 사이에 구분선 추가',
        ],
    ),
    'low_vision': CognitivePreset(
        name='low_vision',
        description='저시력 사용자를 위한 최적화 (대비 힌트, 구조화)',
        rules=[
            '긴 문단을 3문장 이내로 분리',
            '약어를 처음 사용 시 풀어쓰기',
            '헤딩 마크다운 계층 보강',
            '강조 텍스트에 볼드 마크다운 적용',
        ],
    ),
}

# 약어 패턴
_ACRONYM_IN_PARENS = re.compile(r'\(([A-Z]{2,6})\)')

# 문장 분리 패턴
_SENTENCE_END = re.compile(r'(?<=[.!?。])\s+')

# 긴 복합어 패턴 (한글 6자 이상 연속, 공백 없음)
_LONG_COMPOUND = re.compile(r'([가-힣]{6,})')

# 잘 알려진 약어 (풀어쓰기 매핑)
_ACRONYM_EXPANSIONS = {
    'AI': '인공지능(AI)',
    'API': '응용 프로그래밍 인터페이스(API)',
    'URL': '웹 주소(URL)',
    'HTML': '웹 문서 형식(HTML)',
    'CSS': '스타일 시트(CSS)',
    'SEO': '검색엔진 최적화(SEO)',
    'FAQ': '자주 묻는 질문(FAQ)',
    'UI': '사용자 인터페이스(UI)',
    'UX': '사용자 경험(UX)',
    'DB': '데이터베이스(DB)',
    'SaaS': '클라우드 소프트웨어(SaaS)',
    'SDK': '소프트웨어 개발 도구(SDK)',
}


def _split_paragraphs(content: str) -> List[str]:
    """콘텐츠를 문단 단위로 분리합니다."""
    paragraphs = content.split('\n')
    return [p for p in paragraphs if p.strip()]


def _split_into_sentences(paragraph: str) -> List[str]:
    """문단을 문장 단위로 분리합니다."""
    sentences = _SENTENCE_END.split(paragraph.strip())
    return [s.strip() for s in sentences if s.strip()]


def _apply_short_paragraphs(content: str, max_sentences: int = 3) -> str:
    """긴 문단을 max_sentences 이내로 분리합니다."""
    paragraphs = _split_paragraphs(content)
    result = []

    for para in paragraphs:
        # 마크다운 헤딩이나 빈 줄은 그대로 유지
        if para.startswith('#') or para.startswith('---') or para.startswith('```'):
            result.append(para)
            continue

        sentences = _split_into_sentences(para)
        if len(sentences) <= max_sentences:
            result.append(para)
            continue

        # max_sentences 단위로 끊어서 문단 분리
        for i in range(0, len(sentences), max_sentences):
            chunk = sentences[i:i + max_sentences]
            result.append(' '.join(chunk))

    return '\n\n'.join(result)


def _expand_acronyms_first_use(content: str) -> str:
    """약어의 첫 등장을 풀어쓰기로 교체합니다."""
    seen = set()
    result = content

    # 단독 대문자 약어 탐색
    for acronym, expansion in _ACRONYM_EXPANSIONS.items():
        pattern = re.compile(r'(?<![A-Za-z])' + re.escape(acronym) + r'(?![A-Za-z])')
        matches = list(pattern.finditer(result))
        if matches and acronym not in seen:
            # 첫 등장만 교체
            first = matches[0]
            result = result[:first.start()] + expansion + result[first.end():]
            seen.add(acronym)

    return result


def _insert_compound_dots(content: str) -> str:
    """긴 복합어에 가운뎃점(·)을 삽입합니다 (난독증 최적화)."""
    def _split_word(match):
        word = match.group(1)
        if len(word) < 6:
            return word
        # 3글자마다 가운뎃점 삽입
        mid = len(word) // 2
        return word[:mid] + '·' + word[mid:]

    return _LONG_COMPOUND.sub(_split_word, content)


def _bold_first_sentences(content: str) -> str:
    """각 문단의 첫 문장을 볼드 처리합니다 (ADHD 최적화)."""
    paragraphs = _split_paragraphs(content)
    result = []

    for para in paragraphs:
        # 마크다운 헤딩이나 이미 볼드된 텍스트는 건너뜀
        if para.startswith('#') or para.startswith('**') or para.startswith('---'):
            result.append(para)
            continue

        sentences = _split_into_sentences(para)
        if sentences:
            first = sentences[0]
            # 이미 볼드 아닌 경우만
            if not first.startswith('**'):
                sentences[0] = f'**{first}**'
            result.append(' '.join(sentences))
        else:
            result.append(para)

    return '\n\n'.join(result)


def _add_paragraph_separators(content: str) -> str:
    """문단 사이에 구분선을 추가합니다 (ADHD 최적화)."""
    paragraphs = _split_paragraphs(content)
    if len(paragraphs) <= 1:
        return content

    result = []
    for i, para in enumerate(paragraphs):
        result.append(para)
        # 마지막 문단 뒤에는 구분선 불필요
        if i < len(paragraphs) - 1:
            # 헤딩 뒤에는 구분선 불필요
            if not para.startswith('#') and not paragraphs[i + 1].startswith('#'):
                result.append('---')

    return '\n\n'.join(result)


def _enhance_headings(content: str) -> str:
    """헤딩 마크다운 계층을 보강합니다 (저시력 최적화).

    헤딩이 없는 긴 콘텐츠에 섹션 구분용 헤딩을 추가합니다.
    """
    paragraphs = _split_paragraphs(content)
    has_headings = any(p.startswith('#') for p in paragraphs)

    # 이미 헤딩이 있으면 그대로 반환
    if has_headings:
        return content

    # 5문단 이상이면 3문단마다 섹션 헤딩 삽입
    if len(paragraphs) < 5:
        return content

    result = []
    section_num = 1
    for i, para in enumerate(paragraphs):
        if i > 0 and i % 3 == 0:
            result.append(f'### 섹션 {section_num}')
            section_num += 1
        result.append(para)

    return '\n\n'.join(result)


def _bold_emphasis(content: str) -> str:
    """이미 강조된 텍스트(*기울임*)를 볼드(**굵게**)로 보강합니다 (저시력 최적화)."""
    # 단일 * 기울임을 ** 볼드로 변환 (이미 ** 인 건 건너뜀)
    result = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'**\1**', content)
    return result


def list_presets() -> List[CognitivePreset]:
    """사용 가능한 인지 접근성 프리셋 목록을 반환합니다.

    Returns:
        CognitivePreset 객체 리스트
    """
    return list(_PRESETS.values())


def apply_cognitive_preset(content: str, preset: str = 'general') -> str:
    """인지 접근성 프리셋을 콘텐츠에 적용합니다.

    Args:
        content: 변환할 텍스트
        preset: 프리셋 이름 ("general", "dyslexia", "adhd", "low_vision")

    Returns:
        변환된 텍스트

    Raises:
        ValueError: 존재하지 않는 프리셋
    """
    if not content or not content.strip():
        return content or ''

    if preset not in _PRESETS:
        available = ', '.join(_PRESETS.keys())
        raise ValueError(f"알 수 없는 프리셋: '{preset}'. 사용 가능: {available}")

    result = content

    # 공통 규칙 (모든 프리셋)
    result = _apply_short_paragraphs(result, max_sentences=3)
    result = _expand_acronyms_first_use(result)

    # 프리셋별 추가 규칙
    if preset == 'dyslexia':
        result = _insert_compound_dots(result)

    elif preset == 'adhd':
        result = _bold_first_sentences(result)
        result = _add_paragraph_separators(result)

    elif preset == 'low_vision':
        result = _enhance_headings(result)
        result = _bold_emphasis(result)

    return result
