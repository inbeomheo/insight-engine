"""
인포그래픽 변환 서비스

텍스트 콘텐츠를 분석하여 인포그래픽 스펙(레이아웃, 블록, 색상)으로 변환합니다.
통계, 리스트, 헤딩, 타임라인 등을 자동 인식하여 적절한 블록 타입에 매핑합니다.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# 블록 높이 추정치 (px) — 인포그래픽 전체 높이 계산용
_BLOCK_HEIGHTS = {
    'header': 120,
    'stat': 100,
    'text': 80,
    'icon_list': 140,
    'timeline': 160,
    'comparison': 150,
}

# 색상 스킴 정의
COLOR_SCHEMES = {
    'professional': {
        'primary': '#2563EB',
        'secondary': '#1E40AF',
        'accent': '#3B82F6',
        'background': '#F8FAFC',
        'text': '#1E293B',
    },
    'vibrant': {
        'primary': '#7C3AED',
        'secondary': '#DB2777',
        'accent': '#F59E0B',
        'background': '#FEFCE8',
        'text': '#1F2937',
    },
    'minimal': {
        'primary': '#18181B',
        'secondary': '#71717A',
        'accent': '#A1A1AA',
        'background': '#FFFFFF',
        'text': '#27272A',
    },
    'nature': {
        'primary': '#059669',
        'secondary': '#0D9488',
        'accent': '#34D399',
        'background': '#F0FDF4',
        'text': '#064E3B',
    },
}

# 숫자 통계 패턴
_STAT_PATTERN = re.compile(
    r'(?:약\s*)?(\d[\d,]*(?:\.\d+)?)\s*(%|퍼센트|원|달러|만|억|배|개|명|건|회|위|배)',
)

# 리스트 패턴: 번호 매기기 또는 불릿
_LIST_PATTERN = re.compile(r'^\s*(?:\d+[.)]\s|[-*•]\s)', re.MULTILINE)

# 헤딩 패턴: 마크다운 또는 짧은 굵은 텍스트
_HEADING_PATTERN = re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE)

# 시간 순서 패턴
_TIMELINE_PATTERN = re.compile(
    r'(?:\d{4}년|\d{1,2}월|\d분기|Q[1-4]|'
    r'1단계|2단계|3단계|4단계|5단계|'
    r'Phase\s*\d|Step\s*\d)',
    re.IGNORECASE,
)

# 비교 패턴
_COMPARISON_PATTERN = re.compile(
    r'(?:vs\.?|대비|비교|차이|반면|한편)',
    re.IGNORECASE,
)

# 아이콘 매핑 (블록 유형별 기본 아이콘)
_DEFAULT_ICONS = {
    'header': 'title',
    'stat': 'bar_chart',
    'text': 'article',
    'icon_list': 'list',
    'timeline': 'schedule',
    'comparison': 'compare_arrows',
}

# 통계 아이콘 매핑 (단위별)
_STAT_ICONS = {
    '%': 'percent',
    '퍼센트': 'percent',
    '원': 'payments',
    '달러': 'attach_money',
    '명': 'people',
    '개': 'inventory_2',
    '건': 'description',
    '회': 'repeat',
    '배': 'trending_up',
    '만': 'payments',
    '억': 'payments',
    '위': 'emoji_events',
}


@dataclass
class InfoBlock:
    """인포그래픽의 개별 블록"""
    block_type: str  # header, stat, text, icon_list, timeline, comparison
    content: str  # 블록 내용 (텍스트 또는 구조화 데이터)
    icon: str  # 아이콘 식별자 (Material Icons 이름 기준)
    position: int  # 블록 순서 (0-based)


@dataclass
class InfographicSpec:
    """인포그래픽 전체 스펙"""
    title: str
    blocks: List[InfoBlock]
    layout: str  # vertical, two_column, zigzag
    color_scheme: str  # professional, vibrant, minimal, nature
    estimated_height: int  # 예상 전체 높이 (px)


def _extract_title(content: str) -> str:
    """콘텐츠에서 제목을 추출합니다. 마크다운 헤딩 또는 첫 줄 사용."""
    heading_match = _HEADING_PATTERN.search(content)
    if heading_match:
        return heading_match.group(1).strip()

    # 첫 줄을 제목으로 사용
    first_line = content.strip().split('\n')[0].strip()
    if len(first_line) <= 60:
        return first_line
    return first_line[:57] + '...'


def _detect_stats(content: str) -> List[dict]:
    """콘텐츠에서 통계 수치를 추출합니다."""
    stats = []
    for match in _STAT_PATTERN.finditer(content):
        value = match.group(1).replace(',', '')
        unit = match.group(2)

        # 주변 문맥에서 라벨 추출 (수치 앞 20자)
        start = max(0, match.start() - 30)
        context = content[start:match.start()].strip()
        # 마지막 구절 추출
        label_parts = re.split(r'[,.!?\n]', context)
        label = label_parts[-1].strip() if label_parts else '통계'

        stats.append({
            'value': value,
            'unit': unit,
            'label': label,
            'icon': _STAT_ICONS.get(unit, 'bar_chart'),
        })
    return stats


def _detect_lists(content: str) -> List[str]:
    """콘텐츠에서 리스트 항목을 추출합니다."""
    items = []
    for match in _LIST_PATTERN.finditer(content):
        # 해당 줄 전체를 가져옴
        line_start = content.rfind('\n', 0, match.start()) + 1
        line_end = content.find('\n', match.end())
        if line_end == -1:
            line_end = len(content)
        line = content[line_start:line_end].strip()
        # 불릿/번호 제거
        cleaned = re.sub(r'^\s*(?:\d+[.)]\s|[-*•]\s)', '', line).strip()
        if cleaned:
            items.append(cleaned)
    return items


def _detect_timeline_items(content: str) -> List[str]:
    """시간 순서 항목을 추출합니다."""
    items = []
    lines = content.split('\n')
    for line in lines:
        if _TIMELINE_PATTERN.search(line):
            items.append(line.strip())
    return items


def _detect_comparisons(content: str) -> List[str]:
    """비교 구문이 포함된 문장을 추출합니다."""
    sentences = re.split(r'[.!?\n]+', content)
    comparisons = []
    for sentence in sentences:
        if _COMPARISON_PATTERN.search(sentence) and sentence.strip():
            comparisons.append(sentence.strip())
    return comparisons


def _determine_layout(blocks: List[InfoBlock]) -> str:
    """블록 구성에 따라 레이아웃 결정

    - stat 블록이 3개 이상 → two_column (통계 나란히)
    - timeline 블록 존재 → vertical (시간 흐름)
    - 블록 5개 이상 → zigzag (시각적 변화)
    - 기본 → vertical
    """
    stat_count = sum(1 for b in blocks if b.block_type == 'stat')
    has_timeline = any(b.block_type == 'timeline' for b in blocks)

    if has_timeline:
        return 'vertical'
    if stat_count >= 3:
        return 'two_column'
    if len(blocks) >= 5:
        return 'zigzag'
    return 'vertical'


def _determine_color_scheme(content: str) -> str:
    """콘텐츠 특성에 따라 색상 스킴 결정

    - 기술/개발 키워드 → professional
    - 마케팅/크리에이티브 키워드 → vibrant
    - 자연/환경 키워드 → nature
    - 기본 → minimal
    """
    content_lower = content.lower()

    tech_keywords = ['api', '개발', '코드', '서버', '데이터베이스', 'sdk', '프레임워크']
    if any(kw in content_lower for kw in tech_keywords):
        return 'professional'

    creative_keywords = ['마케팅', '브랜드', '캠페인', '디자인', '크리에이티브', '콘텐츠']
    if any(kw in content_lower for kw in creative_keywords):
        return 'vibrant'

    nature_keywords = ['환경', '자연', '지속가능', '친환경', '탄소', '생태']
    if any(kw in content_lower for kw in nature_keywords):
        return 'nature'

    return 'minimal'


def _calculate_height(blocks: List[InfoBlock]) -> int:
    """블록 구성으로 전체 높이 추정 (px)"""
    height = 0
    for block in blocks:
        height += _BLOCK_HEIGHTS.get(block.block_type, 80)
    # 여백 추가 (블록 간 20px + 상하 40px)
    height += max(0, len(blocks) - 1) * 20 + 80
    return height


def convert_to_infographic(content: str) -> InfographicSpec:
    """텍스트 콘텐츠를 인포그래픽 스펙으로 변환합니다.

    콘텐츠에서 통계, 리스트, 타임라인, 비교 구문을 자동 인식하여
    적절한 블록 타입에 매핑합니다.

    Args:
        content: 변환할 텍스트 콘텐츠

    Returns:
        InfographicSpec 데이터클래스 인스턴스
    """
    if not content or not content.strip():
        return InfographicSpec(
            title='인포그래픽',
            blocks=[],
            layout='vertical',
            color_scheme='minimal',
            estimated_height=0,
        )

    content = content.strip()
    blocks: List[InfoBlock] = []
    position = 0

    # 1. 제목 → header 블록
    title = _extract_title(content)
    blocks.append(InfoBlock(
        block_type='header',
        content=title,
        icon=_DEFAULT_ICONS['header'],
        position=position,
    ))
    position += 1

    # 2. 통계 수치 → stat 블록
    stats = _detect_stats(content)
    for stat in stats:
        stat_text = f"{stat['label']}: {stat['value']}{stat['unit']}"
        blocks.append(InfoBlock(
            block_type='stat',
            content=stat_text,
            icon=stat.get('icon', 'bar_chart'),
            position=position,
        ))
        position += 1

    # 3. 타임라인 항목 → timeline 블록
    timeline_items = _detect_timeline_items(content)
    if timeline_items:
        timeline_text = ' → '.join(timeline_items[:6])  # 최대 6개
        blocks.append(InfoBlock(
            block_type='timeline',
            content=timeline_text,
            icon=_DEFAULT_ICONS['timeline'],
            position=position,
        ))
        position += 1

    # 4. 비교 구문 → comparison 블록
    comparisons = _detect_comparisons(content)
    for comp in comparisons[:3]:  # 최대 3개
        blocks.append(InfoBlock(
            block_type='comparison',
            content=comp,
            icon=_DEFAULT_ICONS['comparison'],
            position=position,
        ))
        position += 1

    # 5. 리스트 항목 → icon_list 블록
    list_items = _detect_lists(content)
    if list_items:
        list_text = '\n'.join(f"• {item}" for item in list_items[:8])  # 최대 8개
        blocks.append(InfoBlock(
            block_type='icon_list',
            content=list_text,
            icon=_DEFAULT_ICONS['icon_list'],
            position=position,
        ))
        position += 1

    # 6. 나머지 텍스트 → text 블록 (헤딩 기준 분할)
    # 이미 추출된 내용 외에 의미 있는 텍스트 단락이 있으면 추가
    paragraphs = re.split(r'\n{2,}', content)
    text_block_count = 0
    for para in paragraphs:
        para = para.strip()
        # 이미 추출된 패턴에 해당하지 않는 일반 텍스트만
        if (
            len(para) > 30
            and not _STAT_PATTERN.search(para)
            and not _LIST_PATTERN.search(para)
            and not _TIMELINE_PATTERN.search(para)
            and not _COMPARISON_PATTERN.search(para)
            and not _HEADING_PATTERN.match(para)
            and text_block_count < 3  # 최대 3개 텍스트 블록
        ):
            blocks.append(InfoBlock(
                block_type='text',
                content=para[:200],  # 길이 제한
                icon=_DEFAULT_ICONS['text'],
                position=position,
            ))
            position += 1
            text_block_count += 1

    # position 재정렬
    for idx, block in enumerate(blocks):
        block.position = idx

    # 레이아웃, 색상, 높이 결정
    layout = _determine_layout(blocks)
    color_scheme = _determine_color_scheme(content)
    estimated_height = _calculate_height(blocks)

    spec = InfographicSpec(
        title=title,
        blocks=blocks,
        layout=layout,
        color_scheme=color_scheme,
        estimated_height=estimated_height,
    )

    logger.info(f"인포그래픽 변환: {len(blocks)}개 블록, "
                f"layout={layout}, color={color_scheme}, "
                f"height={estimated_height}px")
    return spec
