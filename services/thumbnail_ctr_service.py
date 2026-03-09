"""썸네일 CTR 예측 서비스

썸네일 변형을 생성하고 규칙 기반으로 CTR(클릭률)을 예측한다.
실제 이미지를 생성하지 않고, 레이아웃/요소/색상 구성을 계획한다.
"""
import hashlib
import re
from dataclasses import dataclass, field


@dataclass
class ThumbnailVariant:
    """썸네일 변형"""
    variant_id: str
    layout: str                # "face_focus" | "text_overlay" | "split" | "minimal"
    predicted_ctr: float       # 0.0~1.0
    elements: list             # 포함 요소
    color_scheme: str


# 레이아웃별 기본 CTR 점수 (업계 평균 기반 추정치)
_LAYOUT_BASE_CTR = {
    "face_focus": 0.08,     # 얼굴 클로즈업 — 높은 CTR
    "text_overlay": 0.065,  # 텍스트 오버레이 — 중간
    "split": 0.055,         # 좌우 분할 — 중간
    "minimal": 0.045,       # 미니멀 — 낮은 편
}

# 레이아웃별 기본 요소 구성
_LAYOUT_ELEMENTS = {
    "face_focus": ["인물 클로즈업", "감정 표현", "배경 블러"],
    "text_overlay": ["핵심 키워드", "대비색 텍스트", "그라디언트 배경"],
    "split": ["비포/애프터", "좌우 대비", "구분선"],
    "minimal": ["단색 배경", "중앙 아이콘", "미니멀 타이포"],
}

# 색상 구성표
_COLOR_SCHEMES = {
    "high_contrast": {"name": "고대비", "ctr_bonus": 0.015},
    "warm": {"name": "따뜻한 톤", "ctr_bonus": 0.01},
    "cool": {"name": "차가운 톤", "ctr_bonus": 0.005},
    "brand": {"name": "브랜드 컬러", "ctr_bonus": 0.008},
    "monochrome": {"name": "모노크롬", "ctr_bonus": 0.003},
}

# CTR 영향 요소 (제목 키워드 기반)
_CTR_BOOST_KEYWORDS = {
    # 호기심 유발 단어 (한국어)
    '비밀': 0.02, '충격': 0.018, '꿀팁': 0.015, '필수': 0.012,
    '실화': 0.015, '핵심': 0.01, '방법': 0.008, '이유': 0.008,
    '추천': 0.01, '최고': 0.012, '무료': 0.015,
    # 숫자 패턴
    'top': 0.01, 'best': 0.01,
}

# 숫자 포함 보너스 (리스트형 제목)
_NUMBER_BONUS = 0.012


def generate_thumbnail_variants(
    video_id: str,
    title: str = "",
    n: int = 4,
) -> list:
    """썸네일 변형 + CTR 예측 (규칙 기반)

    Args:
        video_id: 대상 영상 ID
        title: 영상 제목 (CTR 예측에 활용)
        n: 생성할 변형 수 (1~8, 기본 4)

    Returns:
        list[ThumbnailVariant]: CTR 내림차순 정렬된 변형 목록
    """
    if not video_id or not video_id.strip():
        raise ValueError("video_id는 비어 있을 수 없습니다")

    n = max(1, min(n, 8))

    # 제목 기반 CTR 보정값 계산
    title_boost = _calculate_title_boost(title)

    # 레이아웃별 변형 생성
    layouts = list(_LAYOUT_BASE_CTR.keys())
    color_keys = list(_COLOR_SCHEMES.keys())

    variants = []
    for i in range(n):
        layout = layouts[i % len(layouts)]
        color_key = color_keys[i % len(color_keys)]
        color_info = _COLOR_SCHEMES[color_key]

        # CTR 예측
        base_ctr = _LAYOUT_BASE_CTR[layout]
        predicted_ctr = base_ctr + title_boost + color_info["ctr_bonus"]
        # 변형 간 미세 차이 (결정적)
        variant_offset = (i * 0.003) - (n * 0.001)
        predicted_ctr += variant_offset
        predicted_ctr = max(0.01, min(predicted_ctr, 0.99))
        predicted_ctr = round(predicted_ctr, 4)

        # 요소 구성
        elements = list(_LAYOUT_ELEMENTS[layout])
        # 제목이 있으면 핵심 키워드 요소 추가
        if title:
            keywords = _extract_title_keywords(title)
            if keywords:
                elements.append(f"키워드: {', '.join(keywords[:3])}")

        # 변형 ID 생성 (결정적)
        variant_id = _generate_variant_id(video_id, layout, i)

        variants.append(ThumbnailVariant(
            variant_id=variant_id,
            layout=layout,
            predicted_ctr=predicted_ctr,
            elements=elements,
            color_scheme=color_info["name"],
        ))

    # CTR 내림차순 정렬
    variants.sort(key=lambda v: v.predicted_ctr, reverse=True)
    return variants


def _calculate_title_boost(title: str) -> float:
    """제목 기반 CTR 보정값 계산"""
    if not title:
        return 0.0

    title_lower = title.lower()
    boost = 0.0

    # 키워드 보너스
    for keyword, bonus in _CTR_BOOST_KEYWORDS.items():
        if keyword in title_lower:
            boost += bonus

    # 숫자 포함 보너스 (리스트형: "5가지", "Top 10" 등)
    if re.search(r'\d+', title):
        boost += _NUMBER_BONUS

    # 물음표 보너스 (호기심 유발)
    if '?' in title or '？' in title:
        boost += 0.008

    # 제목 길이 보정 (30~60자 최적)
    title_len = len(title)
    if 30 <= title_len <= 60:
        boost += 0.005
    elif title_len > 80:
        boost -= 0.005

    return round(boost, 4)


def _extract_title_keywords(title: str) -> list:
    """제목에서 핵심 키워드 추출 (간단한 규칙 기반)"""
    # 불용어 제거
    stopwords = {'이', '그', '저', '을', '를', '에', '의', '는', '은', '가', '와', '과', '도'}
    # 한글 단어 추출 (2자 이상)
    words = re.findall(r'[가-힣]{2,}', title)
    keywords = [w for w in words if w not in stopwords]
    return keywords[:5]


def _generate_variant_id(video_id: str, layout: str, index: int) -> str:
    """결정적 변형 ID 생성"""
    raw = f"{video_id}:{layout}:{index}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]
