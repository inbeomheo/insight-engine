"""
DevRel 패키저 서비스 — 개발자 관계 자료 패키징
"""

import uuid
from dataclasses import dataclass, field

VALID_ASSET_TYPES = ("tutorial", "sample_code", "blog_post", "video", "sdk_doc")
VALID_DIFFICULTIES = ("beginner", "intermediate", "advanced")
# 완성된 패키지에 필요한 필수 자산 타입
REQUIRED_ASSET_TYPES = {"tutorial", "sample_code", "sdk_doc"}


@dataclass
class DevRelAsset:
    """개발자 자료 자산"""
    asset_id: str
    asset_type: str  # tutorial / sample_code / blog_post / video / sdk_doc
    title: str
    content: str
    language: str  # ko / en / ja 등
    difficulty: str  # beginner / intermediate / advanced


@dataclass
class DevRelPackage:
    """DevRel 패키지"""
    package_id: str
    name: str
    assets: list  # list[DevRelAsset]
    target_audience: str
    version: str


def create_package(name: str, target_audience: str, version: str = "1.0.0") -> DevRelPackage:
    """패키지 생성"""
    if not name.strip():
        raise ValueError("패키지 이름은 필수입니다")

    return DevRelPackage(
        package_id=str(uuid.uuid4()),
        name=name.strip(),
        assets=[],
        target_audience=target_audience,
        version=version,
    )


def add_asset(package: DevRelPackage, asset_config: dict) -> DevRelPackage:
    """자산 추가

    asset_config: {"type": str, "title": str, "content": str, "language": str, "difficulty": str}
    """
    asset_type = asset_config.get("type", "")
    if asset_type not in VALID_ASSET_TYPES:
        raise ValueError(f"유효하지 않은 자산 타입: {asset_type}. 허용: {VALID_ASSET_TYPES}")

    difficulty = asset_config.get("difficulty", "beginner")
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"유효하지 않은 난이도: {difficulty}. 허용: {VALID_DIFFICULTIES}")

    asset = DevRelAsset(
        asset_id=str(uuid.uuid4()),
        asset_type=asset_type,
        title=asset_config.get("title", ""),
        content=asset_config.get("content", ""),
        language=asset_config.get("language", "ko"),
        difficulty=difficulty,
    )

    package.assets.append(asset)
    return package


def assess_completeness(package: DevRelPackage) -> dict:
    """완성도 평가"""
    existing_types = {a.asset_type for a in package.assets}
    missing = REQUIRED_ASSET_TYPES - existing_types
    total_required = len(REQUIRED_ASSET_TYPES)
    covered = total_required - len(missing)

    return {
        "package_id": package.package_id,
        "total_assets": len(package.assets),
        "required_types": sorted(REQUIRED_ASSET_TYPES),
        "missing_types": sorted(missing),
        "completeness_pct": round(covered / total_required * 100, 1) if total_required > 0 else 100.0,
        "is_complete": len(missing) == 0,
    }


def generate_readme(package: DevRelPackage) -> str:
    """README 생성"""
    lines = [f"# {package.name}"]
    lines.append("")
    lines.append(f"**버전**: {package.version}")
    lines.append(f"**대상**: {package.target_audience}")
    lines.append("")
    lines.append("## 포함 자료")
    lines.append("")

    if not package.assets:
        lines.append("자료가 없습니다.")
    else:
        # 타입별 그룹핑
        by_type = {}
        for a in package.assets:
            by_type.setdefault(a.asset_type, []).append(a)

        for atype in VALID_ASSET_TYPES:
            if atype in by_type:
                lines.append(f"### {atype}")
                for a in by_type[atype]:
                    lines.append(f"- **{a.title}** ({a.language}, {a.difficulty})")
                lines.append("")

    lines.append("---")
    lines.append(f"패키지 ID: `{package.package_id}`")

    return "\n".join(lines)
