"""
범용 사이드카 서비스 — 콘텐츠 옆에 표시할 보조 정보 패널 구성
"""

import re
import uuid
from dataclasses import dataclass, field


@dataclass
class SidecarPanel:
    """사이드카 패널"""
    panel_id: str
    panel_type: str  # glossary / references / notes / outline / stats
    title: str
    items: list = field(default_factory=list)  # list[dict]


VALID_PANEL_TYPES = {"glossary", "references", "notes", "outline", "stats"}

# 패널 타입별 정렬 우선순위
_PANEL_ORDER = {
    "outline": 0,
    "stats": 1,
    "glossary": 2,
    "references": 3,
    "notes": 4,
}


def _new_id(prefix: str = "panel") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def build_glossary_panel(content: str) -> SidecarPanel:
    """전문용어 추출 + 간단 정의 패널 구성

    대문자 약어(예: API, SEO)와 괄호 정의(예: "캐시(Cache)")를 추출합니다.

    Args:
        content: 콘텐츠 텍스트

    Returns:
        SidecarPanel: 용어 해설 패널
    """
    items = []
    seen_terms = set()

    # 1. 대문자 약어 추출 (2~6글자, 한국어 인접도 허용)
    acronyms = re.findall(r'(?<![A-Za-z])([A-Z]{2,6})(?![A-Za-z])', content)
    for acr in acronyms:
        if acr not in seen_terms:
            seen_terms.add(acr)
            items.append({
                "term": acr,
                "definition": f"{acr} (약어)",
                "source": "acronym",
            })

    # 2. 괄호 정의 추출: "한국어(English)" 또는 "용어(설명)"
    paren_defs = re.findall(r'([가-힣a-zA-Z]+)\(([^)]+)\)', content)
    for term, definition in paren_defs:
        key = term.strip()
        if key not in seen_terms and len(key) >= 2:
            seen_terms.add(key)
            items.append({
                "term": key,
                "definition": definition.strip(),
                "source": "parenthetical",
            })

    return SidecarPanel(
        panel_id=_new_id(),
        panel_type="glossary",
        title="용어 해설",
        items=items,
    )


def build_outline_panel(content: str) -> SidecarPanel:
    """목차/아웃라인 추출 (마크다운 헤딩 기반)

    Args:
        content: 콘텐츠 텍스트

    Returns:
        SidecarPanel: 목차 패널
    """
    items = []
    lines = content.splitlines()

    for idx, line in enumerate(lines):
        match = re.match(r'^(#{1,6})\s+(.+)', line.strip())
        if match:
            level = len(match.group(1))
            heading = match.group(2).strip()
            # 마크다운 강조 제거
            heading = re.sub(r'[*_`]', '', heading)
            items.append({
                "level": level,
                "text": heading,
                "line": idx + 1,
            })

    return SidecarPanel(
        panel_id=_new_id(),
        panel_type="outline",
        title="목차",
        items=items,
    )


def build_stats_panel(content: str) -> SidecarPanel:
    """통계 패널 (글자수, 단어수, 문장수, 읽기 시간)

    Args:
        content: 콘텐츠 텍스트

    Returns:
        SidecarPanel: 통계 패널
    """
    # 마크다운 제거 후 순수 텍스트
    clean = re.sub(r'#{1,6}\s+', '', content)
    clean = re.sub(r'[*_`\[\]()]', '', clean)

    char_count = len(clean.replace(" ", "").replace("\n", ""))
    words = clean.split()
    word_count = len(words)

    # 문장 수: 마침표/느낌표/물음표로 구분
    sentences = re.split(r'[.!?。]\s*', clean)
    sentence_count = len([s for s in sentences if s.strip()])

    # 읽기 시간: 한국어 약 500자/분, 영문 약 200단어/분
    # 한글 포함 여부로 판단
    has_korean = bool(re.search(r'[가-힣]', content))
    if has_korean:
        reading_min = max(1, round(char_count / 500))
    else:
        reading_min = max(1, round(word_count / 200))

    items = [
        {"label": "글자수", "value": char_count},
        {"label": "단어수", "value": word_count},
        {"label": "문장수", "value": sentence_count},
        {"label": "예상 읽기 시간", "value": f"{reading_min}분"},
        {"label": "줄 수", "value": len(content.splitlines())},
    ]

    return SidecarPanel(
        panel_id=_new_id(),
        panel_type="stats",
        title="통계",
        items=items,
    )


def combine_panels(panels: list) -> list:
    """패널 병합/정렬 — 타입 우선순위에 따라 정렬

    Args:
        panels: 패널 목록

    Returns:
        list[SidecarPanel]: 정렬된 패널 목록
    """
    return sorted(
        panels,
        key=lambda p: _PANEL_ORDER.get(p.panel_type, 99),
    )
