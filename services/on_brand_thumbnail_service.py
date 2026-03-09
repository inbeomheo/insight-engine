"""
온브랜드 썸네일 서비스 — 브랜드 가이드라인에 맞는 썸네일 메타데이터 생성
"""

import uuid
from dataclasses import dataclass, field


VALID_LOGO_POSITIONS = ("top-left", "top-right", "bottom-left", "bottom-right")
VALID_STYLES = ("minimal", "bold", "playful")
VALID_ASPECT_RATIOS = {
    "16:9": {"width": 1280, "height": 720},
    "4:3": {"width": 1024, "height": 768},
    "1:1": {"width": 1080, "height": 1080},
}
LAYOUT_OPTIONS = ("centered", "left-aligned", "right-aligned", "split")


@dataclass
class BrandGuideline:
    """브랜드 가이드라인"""
    brand_colors: list  # 예: ["#FF0000", "#FFFFFF"]
    font_family: str
    logo_position: str  # top-left / top-right / bottom-left / bottom-right
    style: str  # minimal / bold / playful


@dataclass
class ThumbnailSpec:
    """썸네일 스펙"""
    spec_id: str
    title_text: str
    subtitle_text: str
    layout: str
    colors: dict  # {"primary": ..., "secondary": ..., "background": ...}
    font: str
    logo_position: str
    dimensions: dict  # {"width": int, "height": int}


def generate_spec(title: str, guideline: BrandGuideline, aspect_ratio: str = "16:9") -> ThumbnailSpec:
    """브랜드 준수 썸네일 스펙 생성"""
    dims = VALID_ASPECT_RATIOS.get(aspect_ratio, VALID_ASPECT_RATIOS["16:9"])
    colors = {
        "primary": guideline.brand_colors[0] if guideline.brand_colors else "#000000",
        "secondary": guideline.brand_colors[1] if len(guideline.brand_colors) > 1 else "#FFFFFF",
        "background": guideline.brand_colors[-1] if guideline.brand_colors else "#FFFFFF",
    }

    # 스타일에 따른 레이아웃 선택
    layout_map = {
        "minimal": "centered",
        "bold": "split",
        "playful": "left-aligned",
    }
    layout = layout_map.get(guideline.style, "centered")

    # 제목에서 부제목 분리 (콜론/대시 기준)
    subtitle = ""
    title_text = title
    for sep in [":", " - ", " — "]:
        if sep in title:
            parts = title.split(sep, 1)
            title_text = parts[0].strip()
            subtitle = parts[1].strip()
            break

    return ThumbnailSpec(
        spec_id=str(uuid.uuid4()),
        title_text=title_text,
        subtitle_text=subtitle,
        layout=layout,
        colors=colors,
        font=guideline.font_family,
        logo_position=guideline.logo_position,
        dimensions=dims,
    )


def validate_brand_compliance(spec: ThumbnailSpec, guideline: BrandGuideline) -> list:
    """가이드라인 위반 사항 목록 반환 (빈 리스트면 준수)"""
    issues = []

    # 폰트 체크
    if spec.font != guideline.font_family:
        issues.append(f"폰트 불일치: {spec.font} (기대: {guideline.font_family})")

    # 로고 위치 체크
    if spec.logo_position != guideline.logo_position:
        issues.append(f"로고 위치 불일치: {spec.logo_position} (기대: {guideline.logo_position})")

    # 색상 체크 — 기본 색상이 브랜드 색상에 포함되어야 함
    primary = spec.colors.get("primary", "")
    if primary and primary not in guideline.brand_colors:
        issues.append(f"기본 색상 '{primary}'이(가) 브랜드 색상에 없음")

    secondary = spec.colors.get("secondary", "")
    if secondary and secondary not in guideline.brand_colors:
        issues.append(f"보조 색상 '{secondary}'이(가) 브랜드 색상에 없음")

    return issues


def suggest_variations(spec: ThumbnailSpec, count: int = 3) -> list:
    """변형 제안 (색상 반전, 레이아웃 변경 등)"""
    variations = []

    for i in range(count):
        new_spec = ThumbnailSpec(
            spec_id=str(uuid.uuid4()),
            title_text=spec.title_text,
            subtitle_text=spec.subtitle_text,
            layout=spec.layout,
            colors=dict(spec.colors),
            font=spec.font,
            logo_position=spec.logo_position,
            dimensions=dict(spec.dimensions),
        )

        if i % 3 == 0:
            # 색상 반전
            new_spec.colors = {
                "primary": spec.colors.get("secondary", "#FFFFFF"),
                "secondary": spec.colors.get("primary", "#000000"),
                "background": spec.colors.get("primary", "#000000"),
            }
        elif i % 3 == 1:
            # 레이아웃 변경
            current_idx = LAYOUT_OPTIONS.index(spec.layout) if spec.layout in LAYOUT_OPTIONS else 0
            new_spec.layout = LAYOUT_OPTIONS[(current_idx + 1) % len(LAYOUT_OPTIONS)]
        else:
            # 로고 위치 변경
            pos_list = list(VALID_LOGO_POSITIONS)
            current_idx = pos_list.index(spec.logo_position) if spec.logo_position in pos_list else 0
            new_spec.logo_position = pos_list[(current_idx + 2) % len(pos_list)]

        variations.append(new_spec)

    return variations
