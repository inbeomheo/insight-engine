"""
엔터티 관계 그래프 추출 서비스
자막 텍스트에서 고유명사/핵심 개체를 추출하고 관계 그래프를 생성한다.
"""
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set

logger = logging.getLogger(__name__)

# 엔터티 타입 상수
VALID_ENTITY_TYPES = {"person", "organization", "technology", "concept", "product"}

# 기술/제품 키워드 (대소문자 구분 없이 매칭)
TECHNOLOGY_KEYWORDS = {
    "ai", "api", "ml", "gpt", "llm", "python", "javascript", "typescript",
    "react", "vue", "angular", "docker", "kubernetes", "aws", "azure", "gcp",
    "tensorflow", "pytorch", "node", "java", "rust", "go", "swift",
    "blockchain", "nft", "web3", "saas", "css", "html", "sql", "nosql",
    "linux", "git", "ci/cd", "devops", "microservice", "graphql", "rest",
}

# 조직 키워드 (대소문자 구분)
ORGANIZATION_KEYWORDS = {
    "Google", "Apple", "Microsoft", "Amazon", "Meta", "Facebook", "OpenAI",
    "Netflix", "Tesla", "Samsung", "LG", "Naver", "Kakao", "LINE",
    "IBM", "Intel", "NVIDIA", "AMD", "Anthropic", "DeepMind",
    "GitHub", "GitLab", "Spotify", "Uber", "Airbnb", "Twitter",
}

# 불용어 (추출 제외 단어)
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "this",
    "that", "these", "those", "it", "its", "i", "you", "he",
    "she", "we", "they", "my", "your", "his", "her", "our",
    "and", "or", "but", "not", "so", "if", "then", "else",
    "for", "with", "from", "to", "of", "in", "on", "at", "by",
    # 한국어 불용어
    "이", "그", "저", "것", "수", "등", "및", "더", "또",
    "그리고", "하지만", "그래서", "따라서", "때문에",
}

# 제품 힌트 키워드
PRODUCT_HINTS = {
    "pro", "plus", "max", "ultra", "lite", "mini", "studio",
    "premium", "enterprise", "cloud", "platform", "app",
}


@dataclass
class Entity:
    """추출된 엔터티"""
    name: str
    entity_type: str
    mention_count: int
    first_mention: int  # 문자 위치 (offset)


@dataclass
class Relationship:
    """엔터티 간 관계"""
    source: str
    target: str
    relation_type: str
    strength: float  # 0.0 ~ 1.0


@dataclass
class EntityGraph:
    """엔터티 관계 그래프"""
    entities: List[Entity]
    relationships: List[Relationship]
    total_entities: int


def _classify_entity(name: str) -> str:
    """엔터티 이름으로 타입 분류"""
    name_lower = name.lower()

    # 기술 키워드 매칭
    if name_lower in TECHNOLOGY_KEYWORDS:
        return "technology"

    # 조직 키워드 매칭 (대소문자 구분)
    if name in ORGANIZATION_KEYWORDS:
        return "organization"

    # 제품 힌트 (이름에 제품 키워드 포함)
    lower_parts = name_lower.split()
    if any(p in PRODUCT_HINTS for p in lower_parts):
        return "product"

    # 대문자로 시작하는 2단어 이상: 가능한 인물/조직
    name_parts = name.split()
    if len(name_parts) >= 2 and all(p[0].isupper() for p in name_parts if p):
        return "person"

    # 전체 대문자 약어 (3자 이상): 조직/기술
    if name.isupper() and len(name) >= 3:
        return "organization"

    return "concept"


def _extract_candidates(text: str) -> List[Tuple[str, int]]:
    """텍스트에서 엔터티 후보 추출 (이름, 위치)"""
    candidates = []

    # 영어: 대문자 시작 단어/연속 단어 추출
    en_pattern = re.compile(r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b')
    for match in en_pattern.finditer(text):
        word = match.group(1).strip()
        if word.lower() not in STOP_WORDS and len(word) >= 2:
            candidates.append((word, match.start()))

    # 영어: 전체 대문자 약어 (2자 이상)
    acronym_pattern = re.compile(r'\b([A-Z]{2,}(?:/[A-Z]+)*)\b')
    for match in acronym_pattern.finditer(text):
        word = match.group(1)
        if word.lower() not in STOP_WORDS:
            candidates.append((word, match.start()))

    # 기술 키워드 직접 매칭 (대소문자 무시)
    text_lower = text.lower()
    for kw in TECHNOLOGY_KEYWORDS:
        idx = text_lower.find(kw)
        while idx != -1:
            candidates.append((kw.upper() if len(kw) <= 3 else kw.capitalize(), idx))
            idx = text_lower.find(kw, idx + len(kw))

    return candidates


def _count_mentions(text: str, entity_name: str) -> int:
    """텍스트에서 엔터티 언급 횟수"""
    pattern = re.compile(re.escape(entity_name), re.IGNORECASE)
    return len(pattern.findall(text))


def _build_relationships(
    text: str,
    entities: List[Entity],
    window_size: int = 200,
) -> List[Relationship]:
    """근접 공출현(co-occurrence) 기반 관계 추출

    같은 텍스트 윈도우 내에 함께 등장하면 관계가 있다고 판단한다.
    """
    if len(entities) < 2:
        return []

    text_lower = text.lower()
    # 각 엔터티의 출현 위치 목록
    entity_positions: Dict[str, List[int]] = {}
    for ent in entities:
        pattern = re.compile(re.escape(ent.name), re.IGNORECASE)
        positions = [m.start() for m in pattern.finditer(text)]
        if positions:
            entity_positions[ent.name] = positions

    # 공출현 카운트
    co_occur: Counter = Counter()
    entity_names = list(entity_positions.keys())

    for i in range(len(entity_names)):
        for j in range(i + 1, len(entity_names)):
            name_a = entity_names[i]
            name_b = entity_names[j]
            count = 0
            for pos_a in entity_positions[name_a]:
                for pos_b in entity_positions[name_b]:
                    if abs(pos_a - pos_b) <= window_size:
                        count += 1
            if count > 0:
                co_occur[(name_a, name_b)] = count

    if not co_occur:
        return []

    # 강도 정규화 (최대 공출현 기준)
    max_count = max(co_occur.values())
    relationships = []

    for (source, target), count in co_occur.most_common():
        strength = round(min(count / max(max_count, 1), 1.0), 2)
        # 관계 타입 결정
        source_type = next((e.entity_type for e in entities if e.name == source), "concept")
        target_type = next((e.entity_type for e in entities if e.name == target), "concept")
        relation_type = _infer_relation_type(source_type, target_type)

        relationships.append(Relationship(
            source=source,
            target=target,
            relation_type=relation_type,
            strength=strength,
        ))

    return relationships


def _infer_relation_type(source_type: str, target_type: str) -> str:
    """엔터티 타입 조합으로 관계 타입 추론"""
    pair = frozenset({source_type, target_type})

    if pair == {"person", "organization"}:
        return "affiliated_with"
    if pair == {"person", "technology"}:
        return "uses"
    if pair == {"organization", "technology"}:
        return "develops"
    if pair == {"organization", "product"}:
        return "produces"
    if pair == {"technology", "technology"}:
        return "related_to"
    if pair == {"person", "person"}:
        return "collaborates_with"
    return "associated_with"


def extract_entity_graph(transcript: str) -> EntityGraph:
    """자막 텍스트에서 엔터티 관계 그래프를 추출한다.

    Args:
        transcript: 자막 텍스트

    Returns:
        EntityGraph (entities, relationships, total_entities)
    """
    if not transcript or not transcript.strip():
        logger.warning("자막이 비어 있습니다")
        return EntityGraph(entities=[], relationships=[], total_entities=0)

    transcript = transcript.strip()

    # 후보 추출
    candidates = _extract_candidates(transcript)
    if not candidates:
        logger.info("엔터티 후보가 없습니다")
        return EntityGraph(entities=[], relationships=[], total_entities=0)

    # 중복 제거 + 첫 출현 위치 기록
    first_positions: Dict[str, int] = {}
    for name, pos in candidates:
        normalized = name.strip()
        if normalized not in first_positions or pos < first_positions[normalized]:
            first_positions[normalized] = pos

    # 엔터티 목록 생성
    entities: List[Entity] = []
    seen_lower: Set[str] = set()

    for name, first_pos in sorted(first_positions.items(), key=lambda x: x[1]):
        # 대소문자 중복 제거
        if name.lower() in seen_lower:
            continue
        seen_lower.add(name.lower())

        mention_count = _count_mentions(transcript, name)
        if mention_count < 1:
            continue

        entity_type = _classify_entity(name)
        entities.append(Entity(
            name=name,
            entity_type=entity_type,
            mention_count=mention_count,
            first_mention=first_pos,
        ))

    # 언급 횟수 기준 정렬 (내림차순)
    entities.sort(key=lambda e: e.mention_count, reverse=True)

    # 상위 50개로 제한 (성능)
    entities = entities[:50]

    # 관계 추출
    relationships = _build_relationships(transcript, entities)

    logger.info(
        "엔터티 그래프: %d개 엔터티, %d개 관계",
        len(entities), len(relationships),
    )

    return EntityGraph(
        entities=entities,
        relationships=relationships,
        total_entities=len(entities),
    )
