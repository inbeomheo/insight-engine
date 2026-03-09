"""
구도 고정 변주 서비스 — 동일 구도에서 텍스트/색상만 변경한 변형 생성
"""

import uuid
from dataclasses import dataclass, field

VALID_LAYOUT_TYPES = ("centered", "left-heavy", "right-heavy", "split", "diagonal")


@dataclass
class Composition:
    """구도 정의"""
    comp_id: str
    layout_type: str  # centered / left-heavy / right-heavy / split / diagonal
    text_areas: list  # [{"id": str, "x": int, "y": int, "width": int, "height": int}]
    color_scheme: dict  # {"background": str, "text": str, "accent": str}


@dataclass
class Variant:
    """변형"""
    variant_id: str
    base_comp_id: str
    changes: dict  # {"text_areas": ..., "color_scheme": ...}
    preview_text: str


def create_composition(layout_type: str, text_areas: list, colors: dict) -> Composition:
    """구도 생성"""
    if layout_type not in VALID_LAYOUT_TYPES:
        raise ValueError(f"유효하지 않은 레이아웃: {layout_type}. 허용: {VALID_LAYOUT_TYPES}")
    return Composition(
        comp_id=str(uuid.uuid4()),
        layout_type=layout_type,
        text_areas=text_areas,
        color_scheme=colors,
    )


def generate_variants(composition: Composition, texts: list, color_schemes: list) -> list:
    """텍스트/색상 조합으로 변형 생성"""
    variants = []

    for text in texts:
        for scheme in color_schemes:
            changes = {
                "text": text,
                "color_scheme": scheme,
            }
            # 미리보기: 텍스트 앞 30자
            preview = text[:30] + ("..." if len(text) > 30 else "")

            variant = Variant(
                variant_id=str(uuid.uuid4()),
                base_comp_id=composition.comp_id,
                changes=changes,
                preview_text=preview,
            )
            variants.append(variant)

    return variants


def rank_variants(variants: list) -> list:
    """텍스트 길이/가독성 기반 순위 (짧고 명확한 텍스트 우선)"""

    def _readability_score(variant: Variant) -> float:
        text = variant.changes.get("text", "")
        length = len(text)

        # 최적 길이 20~50자에 가까울수록 높은 점수
        if 20 <= length <= 50:
            length_score = 1.0
        elif length < 20:
            length_score = length / 20.0
        else:
            length_score = max(0.1, 50.0 / length)

        # 공백 비율 (적당한 단어 분리 → 가독성)
        space_ratio = text.count(" ") / max(length, 1)
        space_score = min(1.0, space_ratio * 5)  # 공백 20% 정도가 최적

        return length_score * 0.7 + space_score * 0.3

    return sorted(variants, key=_readability_score, reverse=True)
