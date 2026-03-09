"""
라이선싱 코파일럿 서비스 — 콘텐츠 라이선스 관리 보조
"""

import uuid
from dataclasses import dataclass, field

# 라이선스 정의
LICENSE_DEFINITIONS = {
    "CC-BY": {
        "permissions": ["commercial_use", "modification", "distribution", "private_use"],
        "restrictions": ["attribution_required"],
    },
    "CC-BY-SA": {
        "permissions": ["commercial_use", "modification", "distribution", "private_use"],
        "restrictions": ["attribution_required", "share_alike"],
    },
    "CC-BY-NC": {
        "permissions": ["modification", "distribution", "private_use"],
        "restrictions": ["attribution_required", "non_commercial"],
    },
    "MIT": {
        "permissions": ["commercial_use", "modification", "distribution", "private_use"],
        "restrictions": ["include_license"],
    },
    "proprietary": {
        "permissions": ["private_use"],
        "restrictions": ["no_modification", "no_distribution", "no_commercial_use"],
    },
    "public_domain": {
        "permissions": ["commercial_use", "modification", "distribution", "private_use"],
        "restrictions": [],
    },
}

# 호환성 매트릭스 (결합 가능 여부)
COMPATIBILITY = {
    ("CC-BY", "CC-BY"): True,
    ("CC-BY", "CC-BY-SA"): True,
    ("CC-BY", "MIT"): True,
    ("CC-BY", "public_domain"): True,
    ("CC-BY-SA", "CC-BY-SA"): True,
    ("CC-BY-SA", "MIT"): False,  # SA 조건 충돌
    ("CC-BY-NC", "CC-BY"): False,  # NC 조건 충돌
    ("CC-BY-NC", "CC-BY-NC"): True,
    ("MIT", "MIT"): True,
    ("MIT", "public_domain"): True,
    ("proprietary", "CC-BY"): False,
    ("proprietary", "MIT"): False,
    ("proprietary", "proprietary"): False,
    ("public_domain", "public_domain"): True,
}

# 텍스트 마커 → 라이선스 타입 매핑
MARKER_MAP = {
    "CC BY-SA": "CC-BY-SA",
    "CC BY-NC": "CC-BY-NC",
    "CC BY": "CC-BY",
    "Creative Commons Attribution-ShareAlike": "CC-BY-SA",
    "Creative Commons Attribution-NonCommercial": "CC-BY-NC",
    "Creative Commons Attribution": "CC-BY",
    "MIT License": "MIT",
    "MIT": "MIT",
    "Public Domain": "public_domain",
    "CC0": "public_domain",
    "All Rights Reserved": "proprietary",
    "Proprietary": "proprietary",
    "저작권 보호": "proprietary",
}


@dataclass
class License:
    """라이선스"""
    license_id: str
    license_type: str  # CC-BY / CC-BY-SA / CC-BY-NC / MIT / proprietary / public_domain
    permissions: list
    restrictions: list


@dataclass
class LicenseCheck:
    """라이선스 호환성 체크 결과"""
    content_id: str
    license: License
    compatible: bool
    issues: list


def identify_license(text_markers: str) -> License:
    """텍스트에서 라이선스 식별 (가장 먼저 매칭되는 마커 사용)"""
    # 긴 마커부터 매칭 (CC BY-SA가 CC BY보다 먼저 매칭되도록)
    sorted_markers = sorted(MARKER_MAP.keys(), key=len, reverse=True)

    for marker in sorted_markers:
        if marker.lower() in text_markers.lower():
            lt = MARKER_MAP[marker]
            defn = LICENSE_DEFINITIONS.get(lt, {"permissions": [], "restrictions": []})
            return License(
                license_id=str(uuid.uuid4()),
                license_type=lt,
                permissions=list(defn["permissions"]),
                restrictions=list(defn["restrictions"]),
            )

    # 매칭 없으면 proprietary 기본
    defn = LICENSE_DEFINITIONS["proprietary"]
    return License(
        license_id=str(uuid.uuid4()),
        license_type="proprietary",
        permissions=list(defn["permissions"]),
        restrictions=list(defn["restrictions"]),
    )


def check_compatibility(licenses: list) -> LicenseCheck:
    """라이선스 호환성 체크"""
    issues = []

    if len(licenses) < 2:
        return LicenseCheck(
            content_id=str(uuid.uuid4()),
            license=licenses[0] if licenses else License(
                license_id="", license_type="unknown", permissions=[], restrictions=[],
            ),
            compatible=True,
            issues=[],
        )

    compatible = True
    for i in range(len(licenses)):
        for j in range(i + 1, len(licenses)):
            pair = (licenses[i].license_type, licenses[j].license_type)
            pair_rev = (licenses[j].license_type, licenses[i].license_type)

            is_compat = COMPATIBILITY.get(pair, COMPATIBILITY.get(pair_rev, None))

            if is_compat is None:
                issues.append(f"호환성 정보 없음: {pair[0]} + {pair[1]}")
                compatible = False
            elif not is_compat:
                issues.append(f"비호환: {pair[0]} + {pair[1]}")
                compatible = False

    # 결합 시 가장 제한적인 라이선스 반환
    most_restrictive = max(licenses, key=lambda l: len(l.restrictions))

    return LicenseCheck(
        content_id=str(uuid.uuid4()),
        license=most_restrictive,
        compatible=compatible,
        issues=issues,
    )


def suggest_license(use_case: str) -> License:
    """용도별 라이선스 추천"""
    use_case_lower = use_case.lower()

    if any(k in use_case_lower for k in ["상업", "commercial", "판매", "수익"]):
        lt = "MIT"
    elif any(k in use_case_lower for k in ["공유", "오픈소스", "open source"]):
        lt = "CC-BY-SA"
    elif any(k in use_case_lower for k in ["교육", "학습", "비영리", "non-commercial"]):
        lt = "CC-BY-NC"
    elif any(k in use_case_lower for k in ["자유", "제한없", "public"]):
        lt = "public_domain"
    elif any(k in use_case_lower for k in ["독점", "비공개", "private"]):
        lt = "proprietary"
    else:
        lt = "CC-BY"

    defn = LICENSE_DEFINITIONS[lt]
    return License(
        license_id=str(uuid.uuid4()),
        license_type=lt,
        permissions=list(defn["permissions"]),
        restrictions=list(defn["restrictions"]),
    )


def generate_attribution(license: License, author: str) -> str:
    """저작자 표시 문구 생성"""
    if license.license_type == "public_domain":
        return f"이 저작물은 퍼블릭 도메인입니다. (원작자: {author})"

    if license.license_type == "proprietary":
        return f"© {author}. All Rights Reserved."

    if license.license_type == "MIT":
        return f"Copyright (c) {author}. MIT License."

    # CC 계열
    type_label = license.license_type.replace("-", " ")
    return f"이 저작물은 {type_label} 라이선스로 제공됩니다. 원작자: {author}"
