"""
제품 아바타 서비스

아바타 설명과 제품 설명을 기반으로
제품 시연 데모 시나리오를 생성하는 규칙 기반 서비스.
외부 API 호출 없음.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import uuid
import re


@dataclass
class ProductDemo:
    """제품 데모 시나리오."""
    demo_id: str
    avatar: Dict                 # 아바타 설정
    product: Dict                # 제품 정보
    demo_scenes: List[Dict]      # 시연 장면 목록
    duration_seconds: int        # 전체 예상 시간 (초)


# ── 장면 템플릿 ──
_SCENE_TEMPLATES = {
    "intro": {
        "name": "제품 소개",
        "description": "아바타가 제품을 들고 등장하며 소개",
        "duration": 10,
        "action": "제품을 카메라에 보여주며 인사",
    },
    "feature_showcase": {
        "name": "기능 시연",
        "description": "핵심 기능을 하나씩 보여주는 장면",
        "duration": 15,
        "action": "제품 기능을 순서대로 시연",
    },
    "close_up": {
        "name": "클로즈업",
        "description": "제품 디테일 클로즈업 샷",
        "duration": 8,
        "action": "제품을 카메라 가까이 가져와 디테일 표시",
    },
    "comparison": {
        "name": "비교 시연",
        "description": "이전/이후 또는 경쟁 제품과 비교",
        "duration": 12,
        "action": "비교 대상을 나란히 놓고 차이점 설명",
    },
    "usage_demo": {
        "name": "사용 방법",
        "description": "실제 사용 장면 시연",
        "duration": 15,
        "action": "일상 환경에서 제품 사용 시연",
    },
    "outro": {
        "name": "마무리",
        "description": "제품 요약 및 CTA(행동 유도)",
        "duration": 8,
        "action": "제품을 들고 핵심 메시지 전달",
    },
}

# ── 제품 카테고리 키워드 ──
_CATEGORY_KEYWORDS = {
    "tech": ["전자", "기기", "스마트", "앱", "소프트웨어", "디바이스", "tech", "gadget"],
    "beauty": ["화장품", "스킨케어", "뷰티", "메이크업", "크림", "세럼", "beauty", "cosmetic"],
    "food": ["음식", "식품", "요리", "간식", "음료", "식재료", "food", "beverage"],
    "fashion": ["의류", "패션", "신발", "가방", "액세서리", "fashion", "clothing"],
    "home": ["가구", "인테리어", "주방", "생활", "가전", "home", "furniture"],
}

_CATEGORY_SCENES = {
    "tech": ["intro", "feature_showcase", "usage_demo", "close_up", "outro"],
    "beauty": ["intro", "close_up", "usage_demo", "comparison", "outro"],
    "food": ["intro", "close_up", "usage_demo", "outro"],
    "fashion": ["intro", "close_up", "feature_showcase", "outro"],
    "home": ["intro", "feature_showcase", "usage_demo", "comparison", "outro"],
    "default": ["intro", "feature_showcase", "close_up", "outro"],
}


def _detect_category(product_description: str) -> str:
    """제품 설명에서 카테고리 추론."""
    desc_lower = product_description.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return "default"


def _extract_features(product_description: str) -> List[str]:
    """제품 설명에서 핵심 특징 추출."""
    features = []

    # 쉼표, 마침표, 줄바꿈으로 분리하여 특징 추출
    parts = re.split(r'[,，.。\n]+', product_description)
    for part in parts:
        part = part.strip()
        if len(part) >= 4:  # 최소 4글자 이상만
            features.append(part)

    # 특징이 없으면 전체 설명을 하나의 특징으로
    if not features:
        features = [product_description.strip()]

    return features[:5]  # 최대 5개


def _build_avatar(avatar_description: str) -> Dict:
    """아바타 설명에서 아바타 설정 구성."""
    return {
        "description": avatar_description.strip(),
        "type": "virtual_presenter",
        "interaction": "product_holding",
    }


def _build_product(product_description: str, category: str, features: List[str]) -> Dict:
    """제품 정보 구성."""
    return {
        "description": product_description.strip(),
        "category": category,
        "features": features,
        "feature_count": len(features),
    }


def _build_scenes(category: str, features: List[str], product_description: str) -> List[Dict]:
    """카테고리와 특징에 기반한 데모 장면 생성."""
    scene_order = _CATEGORY_SCENES.get(category, _CATEGORY_SCENES["default"])
    scenes = []
    feature_idx = 0

    for i, scene_key in enumerate(scene_order):
        template = _SCENE_TEMPLATES[scene_key]
        scene = {
            "index": i,
            "scene_type": scene_key,
            "name": template["name"],
            "description": template["description"],
            "action": template["action"],
            "duration_seconds": template["duration"],
        }

        # 기능 시연 장면에 실제 특징 매핑
        if scene_key == "feature_showcase" and feature_idx < len(features):
            scene["featured_item"] = features[feature_idx]
            feature_idx += 1
        elif scene_key == "close_up" and features:
            scene["focus_detail"] = features[0]

        scenes.append(scene)

    return scenes


def hold_product(avatar_description: str, product_description: str) -> ProductDemo:
    """
    제품 아바타 데모 시나리오를 생성한다.

    Args:
        avatar_description: 아바타 외형 설명 (예: "친근한 여성 캐릭터")
        product_description: 제품 설명 (예: "무선 블루투스 이어폰, 노이즈 캔슬링, 30시간 배터리")

    Returns:
        ProductDemo: 데모 시나리오

    Raises:
        ValueError: 설명이 비어있을 때
    """
    if not avatar_description or not avatar_description.strip():
        raise ValueError("아바타 설명이 필요합니다")
    if not product_description or not product_description.strip():
        raise ValueError("제품 설명이 필요합니다")

    # 카테고리 감지
    category = _detect_category(product_description)

    # 특징 추출
    features = _extract_features(product_description)

    # 아바타 설정
    avatar = _build_avatar(avatar_description)

    # 제품 정보
    product = _build_product(product_description, category, features)

    # 장면 생성
    scenes = _build_scenes(category, features, product_description)

    # 전체 시간 계산
    total_duration = sum(s["duration_seconds"] for s in scenes)

    return ProductDemo(
        demo_id=str(uuid.uuid4())[:12],
        avatar=avatar,
        product=product,
        demo_scenes=scenes,
        duration_seconds=total_duration,
    )
