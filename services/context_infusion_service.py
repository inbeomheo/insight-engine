"""태그형 컨텍스트 인퓨전 + 코퍼스 기반 편집 룰북 생성

브랜드 자산(톤, 용어, CTA 등)을 {{brand:tag_name}} 태그로 프롬프트에 주입하여
일관성을 유지하고, 코퍼스(기존 발행물) 분석으로 편집 가이드를 자동 생성한다.
"""

from dataclasses import dataclass, field
import re
import time
from collections import Counter


@dataclass
class BrandAsset:
    """브랜드 자산 태그 하나를 표현하는 데이터 클래스"""
    tag_name: str       # 예: "tone", "cta_style", "terminology"
    content: str        # 실제 값
    user_id: str
    created_at: float = field(default_factory=time.time)


@dataclass
class EditRulebook:
    """코퍼스 분석 결과로 생성되는 편집 가이드"""
    tone_keywords: list[str]          # 선호 톤 키워드
    forbidden_words: list[str]        # 금지어
    preferred_expressions: list[str]  # 선호 표현
    avg_sentence_length: float        # 평균 문장 길이
    formality_level: str              # formal / conversational / casual
    generated_at: float = field(default_factory=time.time)


# 내부 저장소: user_id → tag_name → BrandAsset
_asset_store: dict[str, dict[str, BrandAsset]] = {}

# 태그 패턴: {{brand:tag_name}}
_TAG_PATTERN = re.compile(r'\{\{brand:(\w+)\}\}')

# formality 판정에 사용하는 격식체 어미/표현
_FORMAL_MARKERS = [
    '습니다', '입니다', '하십시오', '됩니다', '있습니다',
    '바랍니다', '드립니다', '하겠습니다',
]
_CASUAL_MARKERS = [
    '해요', '예요', '거든요', '잖아요', '네요', '죠',
    '할게요', '볼게요', '같아요',
]


def register_brand_asset(user_id: str, tag_name: str, content: str) -> BrandAsset:
    """브랜드 자산 태그를 등록하거나 업데이트한다.

    동일 user_id + tag_name 조합이 이미 존재하면 content를 갱신한다.
    """
    asset = BrandAsset(
        tag_name=tag_name,
        content=content,
        user_id=user_id,
    )

    if user_id not in _asset_store:
        _asset_store[user_id] = {}

    _asset_store[user_id][tag_name] = asset
    return asset


def get_brand_assets(user_id: str) -> list[BrandAsset]:
    """사용자의 모든 브랜드 자산 태그를 반환한다."""
    if user_id not in _asset_store:
        return []
    return list(_asset_store[user_id].values())


def delete_brand_asset(user_id: str, tag_name: str) -> bool:
    """브랜드 자산 태그를 삭제한다. 삭제 성공 시 True, 미존재 시 False."""
    if user_id not in _asset_store:
        return False
    if tag_name not in _asset_store[user_id]:
        return False

    del _asset_store[user_id][tag_name]

    # 사용자의 태그가 모두 삭제되면 사용자 키도 정리
    if not _asset_store[user_id]:
        del _asset_store[user_id]

    return True


def inject_tags(prompt: str, user_id: str) -> str:
    """프롬프트 내 {{brand:tag_name}} 패턴을 실제 값으로 치환한다.

    등록된 태그는 해당 content로, 미등록 태그는 '[미설정: tag_name]'으로 대체한다.
    """
    user_assets = _asset_store.get(user_id, {})

    def _replace(match: re.Match) -> str:
        tag_name = match.group(1)
        asset = user_assets.get(tag_name)
        if asset:
            return asset.content
        return f'[미설정: {tag_name}]'

    return _TAG_PATTERN.sub(_replace, prompt)


def generate_rulebook(corpus_texts: list[str]) -> EditRulebook:
    """코퍼스(기존 발행물 텍스트 모음)를 분석하여 편집 룰북을 생성한다.

    - 단어 빈도 분석으로 톤 키워드·선호 표현 추출
    - 평균 문장 길이 계산
    - 격식체/비격식체 비율로 formality 판정
    """
    if not corpus_texts:
        return EditRulebook(
            tone_keywords=[],
            forbidden_words=[],
            preferred_expressions=[],
            avg_sentence_length=0.0,
            formality_level='conversational',
        )

    # 전체 텍스트 합치기
    all_text = '\n'.join(corpus_texts)

    # 문장 분리 (마침표, 느낌표, 물음표 기준)
    sentences = re.split(r'[.!?。]+', all_text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # 평균 문장 길이 (글자 수 기준)
    avg_sentence_length = 0.0
    if sentences:
        total_chars = sum(len(s) for s in sentences)
        avg_sentence_length = round(total_chars / len(sentences), 1)

    # 단어 빈도 분석 (2글자 이상 한글/영문 단어)
    words = re.findall(r'[가-힣a-zA-Z]{2,}', all_text)
    word_counts = Counter(words)

    # 불용어 필터링 (한국어 일반 불용어)
    stopwords = {
        '그리고', '하지만', '그래서', '때문에', '그런데', '그러나',
        '또한', '이런', '저런', '이것', '그것', '하는', '있는',
        '되는', '위한', '대한', '통해', '따라', '에서', '으로',
        '하고', '이고', '에게', '부터', '까지', '에서는',
    }

    # 빈도 상위 단어에서 불용어 제거
    filtered_counts = {
        w: c for w, c in word_counts.items()
        if w not in stopwords
    }
    sorted_words = sorted(filtered_counts.items(), key=lambda x: x[1], reverse=True)

    # 톤 키워드: 상위 10개
    tone_keywords = [w for w, _ in sorted_words[:10]]

    # 선호 표현: 3회 이상 등장한 2~4글자 단어 (상위 10개)
    preferred_expressions = [
        w for w, c in sorted_words
        if c >= 3 and 2 <= len(w) <= 4
    ][:10]

    # 금지어 판정: 프로젝트 기본 금지 표현 목록에서 코퍼스에 등장하는 것 추출
    base_forbidden = [
        '놀라운', '혁신적', '획기적', '최고의', '게임체인저',
        '압도적', '경이로운', '드디어', '탁월한', '인상적',
        '뛰어난', '강력한',
    ]
    forbidden_words = [w for w in base_forbidden if w in filtered_counts]

    # formality 판정
    formality_level = _determine_formality(all_text)

    return EditRulebook(
        tone_keywords=tone_keywords,
        forbidden_words=forbidden_words,
        preferred_expressions=preferred_expressions,
        avg_sentence_length=avg_sentence_length,
        formality_level=formality_level,
    )


def _determine_formality(text: str) -> str:
    """텍스트의 격식 수준을 판정한다.

    격식체 어미(습니다, 입니다 등)와 비격식체 어미(해요, 거든요 등)의
    출현 빈도를 비교하여 formal / conversational / casual을 반환한다.
    """
    formal_count = sum(text.count(marker) for marker in _FORMAL_MARKERS)
    casual_count = sum(text.count(marker) for marker in _CASUAL_MARKERS)

    total = formal_count + casual_count
    if total == 0:
        return 'conversational'

    formal_ratio = formal_count / total

    if formal_ratio >= 0.7:
        return 'formal'
    elif formal_ratio <= 0.3:
        return 'casual'
    else:
        return 'conversational'
