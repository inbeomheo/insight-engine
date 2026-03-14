"""
Entity Coverage Analyzer 서비스

콘텐츠에서 엔터티(사람, 브랜드, 제품, 기술, 개념, 조직)를 규칙 기반으로 추출하고,
관계(동시 등장)와 누락 엔터티를 분석합니다. AI API 호출 없이 동작합니다.
"""
import re
from collections import Counter, defaultdict
from typing import List, Dict, Any


# ── 알려진 엔터티 사전 ──────────────────────────────────────────────

KNOWN_BRANDS = {
    "Google", "Apple", "Microsoft", "Amazon", "Meta",
    "Samsung", "Naver", "Kakao", "OpenAI", "Anthropic",
    "Tesla", "Netflix", "Spotify", "Adobe", "Slack",
    "Notion", "GitHub", "Docker", "AWS", "Azure",
    "IBM", "Oracle", "Intel", "NVIDIA", "Sony",
}

KNOWN_TECHNOLOGIES = {
    "AI", "ML", "Python", "JavaScript", "React",
    "Node", "Docker", "Kubernetes", "API", "REST",
    "GraphQL", "SQL", "NoSQL", "DevOps", "CI/CD",
    "Cloud", "Blockchain", "IoT", "5G", "ChatGPT",
    "TypeScript", "Go", "Rust", "Java", "C++",
    "Flutter", "Swift", "Django", "Flask", "FastAPI",
    "NLP", "LLM", "GPU", "CPU", "SaaS",
}

KNOWN_PRODUCTS = {
    "ChatGPT", "GPT-4", "GPT-3", "Claude", "Gemini",
    "iPhone", "Galaxy", "Windows", "macOS", "Chrome",
    "VS Code", "Copilot", "Siri", "Alexa", "Bard",
    "DALL-E", "Midjourney", "Stable Diffusion",
    "iPad", "MacBook", "Surface", "Pixel",
}

CONCEPT_KEYWORDS = {
    "전략", "혁신", "성장", "분석", "최적화",
    "자동화", "플랫폼", "프레임워크", "아키텍처", "인프라",
    "스케일링", "마이그레이션", "리팩토링", "디지털 전환", "데이터",
    "보안", "거버넌스", "컴플라이언스", "생산성", "효율성",
}

# person 접미어 패턴 (한국어)
_PERSON_SUFFIX_PATTERN = re.compile(
    r'([가-힣]{2,4})\s*(님|씨|대표|교수|박사|이사|사장|회장|위원|의원|장관)'
)

# 영문 이름 패턴 (대문자 시작 2단어)
_ENGLISH_NAME_PATTERN = re.compile(
    r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b'
)

# CEO/CTO 등 직함 앞 이름
_TITLE_NAME_PATTERN = re.compile(
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:CEO|CTO|CFO|COO|VP)\b'
)

# 조직 접미어 패턴 (한국어)
_ORG_SUFFIX_PATTERN = re.compile(
    r'([가-힣A-Za-z]{2,})\s*(회사|기업|연구소|대학|대학교|협회|재단|학회|센터|원|부|처|청)'
)

# 영문 약어 패턴 (2-6자 대문자)
_ACRONYM_PATTERN = re.compile(r'\b([A-Z]{2,6})\b')

# 대문자로 시작하는 고유명사 (단일 단어)
_PROPER_NOUN_PATTERN = re.compile(r'\b([A-Z][a-z]{2,})\b')

# 문장 분리 패턴
_SENTENCE_SPLIT = re.compile(r'[.!?\n]+')

# 제품명에서 기술명과 겹치는 항목 (제품 우선)
_PRODUCT_TECH_OVERLAP = KNOWN_PRODUCTS & KNOWN_TECHNOLOGIES  # ChatGPT 등

_EMPTY_RESULT = {
    "entities": [],
    "entity_density": 0.0,
    "type_distribution": {},
    "relationships": [],
    "coverage_score": 0,
    "suggestions": ["콘텐츠에서 엔터티가 감지되지 않았습니다. 구체적인 브랜드, 기술명, 인물명을 추가하세요."],
}

# 약어 필터 (일반 영어 단어)
_ACRONYM_STOPWORDS = {"THE", "AND", "FOR", "BUT", "NOT", "ARE", "WAS", "HAS", "HAD", "HIS", "HER", "HIM", "ITS"}


def _split_sentences(content: str) -> List[str]:
    """콘텐츠를 문장 단위로 분리합니다."""
    raw = _SENTENCE_SPLIT.split(content)
    return [s.strip() for s in raw if s.strip()]


def _count_words(content: str) -> int:
    """전체 단어 수를 계산합니다. 한국어 + 영문 혼합 기준."""
    # 영문 단어
    english_words = re.findall(r'[A-Za-z]+(?:[-/][A-Za-z]+)*', content)
    # 한국어 어절
    korean_words = re.findall(r'[가-힣]+', content)
    return len(english_words) + len(korean_words)


def _extract_context(content: str, entity_name: str, window: int = 30) -> str:
    """엔터티의 첫 등장 위치 주변 문맥을 추출합니다 (전후 window 자)."""
    idx = content.find(entity_name)
    if idx == -1:
        # 대소문자 무시 검색
        lower_content = content.lower()
        idx = lower_content.find(entity_name.lower())
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(content), idx + len(entity_name) + window)
    context = content[start:end].strip()
    if start > 0:
        context = "..." + context
    if end < len(content):
        context = context + "..."
    return context


def _count_occurrences(content: str, entity_name: str) -> int:
    """엔터티의 등장 횟수를 계산합니다. 대소문자 구분."""
    # 정확한 단어 경계 매칭
    pattern = re.escape(entity_name)
    return len(re.findall(pattern, content))


def _detect_dictionary_entities(content: str) -> Dict[str, str]:
    """사전 기반 엔터티(제품/브랜드/기술)를 감지합니다."""
    found = {}
    for product in KNOWN_PRODUCTS:
        if product in content:
            found[product] = "product"
    for brand in KNOWN_BRANDS:
        if brand in content and brand not in found:
            found[brand] = "brand"
    for tech in KNOWN_TECHNOLOGIES:
        if tech in content and tech not in found:
            found[tech] = "technology"
    return found


def _detect_pattern_entities(content: str, found: Dict[str, str]) -> None:
    """패턴 기반 엔터티(약어/인물/조직/개념)를 감지하여 found에 추가합니다."""
    for match in _ACRONYM_PATTERN.finditer(content):
        acronym = match.group(1)
        if acronym not in found and acronym not in _ACRONYM_STOPWORDS:
            found[acronym] = "technology"

    for match in _PERSON_SUFFIX_PATTERN.finditer(content):
        name = match.group(1)
        if name not in found:
            found[name] = "person"

    for match in _TITLE_NAME_PATTERN.finditer(content):
        name = match.group(1)
        if name not in found:
            found[name] = "person"

    for match in _ENGLISH_NAME_PATTERN.finditer(content):
        full_name = match.group(0)
        words = full_name.split()
        if not any(w in found for w in words) and full_name not in found:
            found[full_name] = "person"

    for match in _ORG_SUFFIX_PATTERN.finditer(content):
        org_name = match.group(0).strip()
        base = match.group(1)
        if base not in found and org_name not in found:
            found[org_name] = "organization"

    for concept in CONCEPT_KEYWORDS:
        count = content.count(concept)
        if count >= 2 and concept not in found:
            found[concept] = "concept"


def _extract_entities(content: str) -> List[Dict[str, Any]]:
    """콘텐츠에서 모든 유형의 엔터티를 추출합니다."""
    found = _detect_dictionary_entities(content)
    _detect_pattern_entities(content, found)

    entities = []
    for name, entity_type in found.items():
        count = _count_occurrences(content, name)
        if count > 0:
            entities.append({
                "name": name,
                "type": entity_type,
                "count": count,
                "context": _extract_context(content, name),
            })

    entities.sort(key=lambda e: e["count"], reverse=True)
    return entities


def _find_relationships(
    content: str, entities: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """같은 문장에 동시 등장하는 엔터티 쌍의 관계를 찾습니다."""
    sentences = _split_sentences(content)
    entity_names = [e["name"] for e in entities]
    co_occurrences: Dict[tuple, int] = Counter()

    for sentence in sentences:
        # 이 문장에 등장하는 엔터티 목록
        present = [name for name in entity_names if name in sentence]
        # 모든 쌍 조합
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                pair = tuple(sorted([present[i], present[j]]))
                co_occurrences[pair] += 1

    relationships = []
    for (e1, e2), count in co_occurrences.most_common():
        relationships.append({
            "entity1": e1,
            "entity2": e2,
            "co_occurrence": count,
        })

    return relationships


def _calculate_coverage_score(
    entities: List[Dict[str, Any]],
    type_distribution: Dict[str, int],
    entity_density: float,
) -> float:
    """커버리지 점수를 계산합니다 (0-100).

    - 엔터티 다양성: 고유 엔터티 수 × 5 (최대 40)
    - 타입 다양성: 사용된 타입 수 × 10 (최대 30)
    - 밀도 적정성: 1-5% → +30, 그 외 → +15
    """
    # 엔터티 다양성
    unique_count = len(entities)
    diversity_score = min(unique_count * 5, 40)

    # 타입 다양성
    type_count = len(type_distribution)
    type_score = min(type_count * 10, 30)

    # 밀도 적정성
    if 1.0 <= entity_density <= 5.0:
        density_score = 30
    else:
        density_score = 15

    score = diversity_score + type_score + density_score
    return min(max(score, 0), 100)


def _generate_suggestions(
    entities: List[Dict[str, Any]],
    type_distribution: Dict[str, int],
    entity_density: float,
) -> List[str]:
    """분석 결과 기반 개선 제안을 생성합니다."""
    suggestions = []
    used_types = set(type_distribution.keys())
    all_types = {"person", "brand", "product", "technology", "concept", "organization"}
    missing_types = all_types - used_types

    if not entities:
        suggestions.append("콘텐츠에서 엔터티가 감지되지 않았습니다. 구체적인 브랜드, 기술명, 인물명을 추가하세요.")
        return suggestions

    # 누락된 엔터티 타입 제안
    type_labels = {
        "person": "인물",
        "brand": "브랜드",
        "product": "제품",
        "technology": "기술",
        "concept": "개념",
        "organization": "조직",
    }
    for missing in missing_types:
        label = type_labels.get(missing, missing)
        suggestions.append(f"'{label}' 유형의 엔터티가 없습니다. 관련 {label}을(를) 언급하면 콘텐츠가 풍부해집니다.")

    # 밀도 관련 제안
    if entity_density < 1.0:
        suggestions.append("엔터티 밀도가 낮습니다 (1% 미만). 구체적인 고유명사를 더 활용하세요.")
    elif entity_density > 5.0:
        suggestions.append("엔터티 밀도가 높습니다 (5% 초과). 엔터티 나열보다 설명과 분석을 보강하세요.")

    # 단일 등장 엔터티가 많은 경우
    single_mention = [e for e in entities if e["count"] == 1]
    if len(single_mention) > len(entities) * 0.7 and len(entities) >= 3:
        suggestions.append("한 번만 언급된 엔터티가 많습니다. 핵심 엔터티를 반복 언급하여 주제를 강화하세요.")

    return suggestions


def analyze_entities(content: str) -> dict:
    """콘텐츠에서 엔터티를 추출하고 관계와 커버리지를 분석합니다.

    Args:
        content: 분석할 텍스트 콘텐츠

    Returns:
        entities, entity_density, type_distribution, relationships,
        coverage_score, suggestions를 포함하는 딕셔너리
    """
    # 빈 콘텐츠 처리
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    # 엔터티 추출
    entities = _extract_entities(content)

    # 단어 수 계산
    word_count = _count_words(content)

    # 엔터티 밀도 계산 (엔터티 수 / 전체 단어 수 × 100)
    total_entity_mentions = sum(e["count"] for e in entities)
    entity_density = (total_entity_mentions / word_count * 100) if word_count > 0 else 0.0
    entity_density = round(entity_density, 2)

    # 타입 분포
    type_distribution: Dict[str, int] = defaultdict(int)
    for entity in entities:
        type_distribution[entity["type"]] += 1
    type_distribution = dict(type_distribution)

    # 관계 분석
    relationships = _find_relationships(content, entities)

    # 커버리지 점수
    coverage_score = _calculate_coverage_score(entities, type_distribution, entity_density)

    # 제안 생성
    suggestions = _generate_suggestions(entities, type_distribution, entity_density)

    return {
        "entities": entities,
        "entity_density": entity_density,
        "type_distribution": type_distribution,
        "relationships": relationships,
        "coverage_score": coverage_score,
        "suggestions": suggestions,
    }
