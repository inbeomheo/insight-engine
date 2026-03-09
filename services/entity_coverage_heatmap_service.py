"""엔터티 커버리지 히트맵 서비스 -- 콘텐츠 내 엔터티 언급 분석"""
import re
from dataclasses import dataclass, field


@dataclass
class EntityCoverage:
    """개별 엔터티 커버리지"""
    entity: str = ""
    mentioned: bool = False
    competitor_mentioned: bool = False
    frequency: int = 0


@dataclass
class EntityHeatmap:
    """엔터티 커버리지 히트맵"""
    entities: list = field(default_factory=list)  # list[EntityCoverage]
    coverage_score: float = 0.0
    gaps: list = field(default_factory=list)  # list[str]


def _extract_entities(content: str) -> list[str]:
    """콘텐츠에서 엔터티(고유명사, 키워드)를 추출한다.

    간이 추출: 대문자로 시작하는 단어 또는 한글 명사 패턴.
    """
    entities = set()
    # 영문 고유명사 (2글자 이상, 대문자 시작)
    for m in re.finditer(r'\b([A-Z][a-zA-Z]{1,})\b', content):
        entities.add(m.group(1))
    # 한글 명사 패턴 (2~10글자)
    for m in re.finditer(r'([가-힣]{2,10})', content):
        word = m.group(1)
        # 조사/어미 제거 (간이)
        if not word.endswith(('은', '는', '이', '가', '을', '를', '에', '의', '로', '와', '과', '도')):
            entities.add(word)
    return sorted(entities)


def _count_entity(content: str, entity: str) -> int:
    """콘텐츠에서 엔터티 등장 횟수를 센다 (대소문자 무시)."""
    return len(re.findall(re.escape(entity), content, re.IGNORECASE))


def generate_entity_heatmap(
    content: str,
    competitors: list[dict] | None = None,
) -> EntityHeatmap:
    """콘텐츠의 엔터티 커버리지 히트맵을 생성한다.

    Args:
        content: 분석 대상 콘텐츠
        competitors: [{"name": "경쟁사A", "content": "..."}] (선택)

    Returns:
        EntityHeatmap
    """
    if not content or not content.strip():
        return EntityHeatmap()

    # 내 콘텐츠에서 엔터티 추출
    my_entities = _extract_entities(content)

    # 경쟁사 콘텐츠에서 엔터티 추출
    competitor_entities: set[str] = set()
    competitor_content_combined = ""
    if competitors:
        for comp in competitors:
            comp_content = comp.get("content", "")
            competitor_content_combined += " " + comp_content
            competitor_entities.update(_extract_entities(comp_content))

    # 전체 엔터티 = 내 것 + 경쟁사 것
    all_entities = sorted(set(my_entities) | competitor_entities)

    coverages: list[EntityCoverage] = []
    gaps: list[str] = []
    mentioned_count = 0

    for entity in all_entities:
        freq = _count_entity(content, entity)
        mentioned = freq > 0
        comp_mentioned = bool(
            competitor_content_combined
            and _count_entity(competitor_content_combined, entity) > 0
        )

        coverages.append(EntityCoverage(
            entity=entity,
            mentioned=mentioned,
            competitor_mentioned=comp_mentioned,
            frequency=freq,
        ))

        if mentioned:
            mentioned_count += 1

        # 경쟁사에는 있지만 내 콘텐츠에 없으면 갭
        if not mentioned and comp_mentioned:
            gaps.append(entity)

    coverage_score = round(mentioned_count / len(all_entities), 4) if all_entities else 0.0

    return EntityHeatmap(
        entities=coverages,
        coverage_score=coverage_score,
        gaps=gaps,
    )
