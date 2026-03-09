"""환경 변화 재프레이밍 서비스 — 콘텐츠를 변화된 환경에 맞게 재구성"""
import re
from dataclasses import dataclass


@dataclass
class ReframedContent:
    """재프레이밍된 콘텐츠"""
    original: str
    reframed: str
    change_type: str  # regulation, technology, market, social
    adaptations: list  # list[str] — 적용된 변화 항목


_VALID_CHANGE_TYPES = {"regulation", "technology", "market", "social"}

# 변화 유형별 관점 전환 규칙
_CHANGE_FRAMES: dict[str, dict] = {
    "regulation": {
        "perspective": "규제 환경 변화",
        "lens": "컴플라이언스 및 법적 준수",
        "adaptations_template": [
            "규제 준수 관점에서 재해석",
            "법적 리스크 요소 식별 및 대응 방안 제시",
            "규제 변화에 따른 기회 요인 도출",
        ],
        "prefix": "⚖️ 규제 환경 관점에서 살펴보면,",
        "keywords": ["규제", "법률", "정책", "가이드라인", "컴플라이언스", "준수"],
    },
    "technology": {
        "perspective": "기술 변화",
        "lens": "기술 혁신과 디지털 전환",
        "adaptations_template": [
            "신기술 도입 가능성 분석",
            "기존 기술 대비 개선점 도출",
            "기술 전환에 따른 실행 로드맵 제안",
        ],
        "prefix": "🔧 기술 변화 관점에서 재조명하면,",
        "keywords": ["기술", "혁신", "디지털", "자동화", "AI", "플랫폼"],
    },
    "market": {
        "perspective": "시장 변화",
        "lens": "시장 트렌드와 경쟁 구도",
        "adaptations_template": [
            "시장 트렌드에 맞춘 포지셔닝 재설정",
            "경쟁 환경 변화에 따른 차별화 전략",
            "새로운 시장 기회 식별",
        ],
        "prefix": "📊 시장 변화 관점에서 분석하면,",
        "keywords": ["시장", "고객", "수요", "경쟁", "트렌드", "성장"],
    },
    "social": {
        "perspective": "사회 변화",
        "lens": "사회적 가치와 문화 변화",
        "adaptations_template": [
            "사회적 가치 관점에서 의미 재해석",
            "문화 변화에 부합하는 메시지 조정",
            "사회적 영향력 극대화 방안 제시",
        ],
        "prefix": "🌍 사회 변화 관점에서 바라보면,",
        "keywords": ["사회", "문화", "가치", "인식", "세대", "다양성"],
    },
}


def _apply_frame(content: str, frame: dict) -> str:
    """프레임을 적용하여 콘텐츠를 재구성한다."""
    paragraphs = content.split("\n\n")
    if not paragraphs:
        return content

    reframed_parts = []

    # 도입부: 프레임 관점 제시
    reframed_parts.append(f"{frame['prefix']}\n")

    # 각 문단을 프레임 렌즈로 재구성
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue

        # 첫 문단: 변화 맥락 설정
        if i == 0:
            reframed_parts.append(
                f"{frame['perspective']} 속에서 이 내용은 새로운 의미를 가집니다.\n\n{para}"
            )
        else:
            # 키워드 강조 삽입
            enhanced = _enhance_with_keywords(para, frame["keywords"])
            reframed_parts.append(enhanced)

    # 마무리: 적응 방향 요약
    reframed_parts.append(
        f"\n{frame['lens']}의 관점에서, 위 내용은 변화하는 환경에 적극적으로 대응할 필요가 있음을 시사합니다."
    )

    return "\n\n".join(reframed_parts)


def _enhance_with_keywords(paragraph: str, keywords: list[str]) -> str:
    """문단에 프레임 키워드가 있으면 강조한다."""
    result = paragraph
    for kw in keywords:
        if kw in result:
            # 첫 등장만 강조 (과잉 표시 방지)
            result = result.replace(kw, f"**{kw}**", 1)
            break
    return result


def _identify_adaptations(content: str, frame: dict) -> list[str]:
    """콘텐츠에서 실제 적용 가능한 변화 항목을 식별한다."""
    adaptations = list(frame["adaptations_template"])

    # 콘텐츠에서 프레임 키워드가 언급되면 구체적 항목 추가
    content_lower = content.lower()
    mentioned_keywords = [kw for kw in frame["keywords"] if kw.lower() in content_lower]

    if mentioned_keywords:
        adaptations.append(
            f"기존 콘텐츠에서 언급된 '{', '.join(mentioned_keywords[:3])}' 관련 내용 업데이트"
        )

    return adaptations


def reframe_for_change(content: str, change_type: str) -> ReframedContent:
    """콘텐츠를 환경 변화에 맞게 재프레이밍한다.

    Args:
        content: 원본 콘텐츠
        change_type: 변화 유형 (regulation, technology, market, social)

    Returns:
        ReframedContent 구조
    """
    if not content or not content.strip():
        return ReframedContent(
            original="",
            reframed="",
            change_type=change_type or "technology",
            adaptations=[],
        )

    # 유효하지 않은 change_type은 technology 폴백
    if change_type not in _VALID_CHANGE_TYPES:
        change_type = "technology"

    frame = _CHANGE_FRAMES[change_type]
    reframed = _apply_frame(content, frame)
    adaptations = _identify_adaptations(content, frame)

    return ReframedContent(
        original=content,
        reframed=reframed,
        change_type=change_type,
        adaptations=adaptations,
    )
