"""
프라이빗 PWA 서비스.

PWA 매니페스트(manifest.json) 및 서비스워커 설정 메타데이터를 생성한다.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PWAConfig:
    """PWA 설정."""
    app_name: str
    short_name: str
    theme_color: str
    background_color: str
    display: str  # standalone / fullscreen / minimal-ui
    start_url: str
    icons: list  # list[dict] — [{src, sizes, type}]
    scope: str = "/"


# 유효한 display 모드
_VALID_DISPLAYS = {"standalone", "fullscreen", "minimal-ui", "browser"}

# 16진 색상 패턴 (#RGB or #RRGGBB)
_HEX_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def generate_manifest(config: PWAConfig) -> dict:
    """manifest.json 데이터를 생성한다."""
    manifest = {
        "name": config.app_name,
        "short_name": config.short_name,
        "theme_color": config.theme_color,
        "background_color": config.background_color,
        "display": config.display,
        "start_url": config.start_url,
        "scope": config.scope,
        "icons": list(config.icons),
    }
    return manifest


def generate_sw_config(
    cache_strategy: str,
    routes: list,
) -> dict:
    """서비스워커 설정을 생성한다.

    Args:
        cache_strategy: cache-first / network-first / stale-while-revalidate
        routes: 캐싱 대상 라우트 목록
    """
    valid_strategies = {"cache-first", "network-first", "stale-while-revalidate"}
    if cache_strategy not in valid_strategies:
        cache_strategy = "network-first"  # 안전한 기본값

    return {
        "cache_strategy": cache_strategy,
        "routes": list(routes),
        "cache_name": "pwa-cache-v1",
        "max_age_seconds": 86400,  # 24시간
        "max_entries": 100,
    }


def validate_config(config: PWAConfig) -> list:
    """PWA 설정을 검증하고 오류 목록을 반환한다."""
    errors = []

    # 필수 필드 검증
    if not config.app_name or not config.app_name.strip():
        errors.append("app_name은 필수입니다")
    if not config.short_name or not config.short_name.strip():
        errors.append("short_name은 필수입니다")
    if not config.start_url or not config.start_url.strip():
        errors.append("start_url은 필수입니다")

    # 색상 형식 검증
    if not _HEX_COLOR_RE.match(config.theme_color or ""):
        errors.append(f"theme_color 형식이 올바르지 않습니다: {config.theme_color} (예: #FF0000)")
    if not _HEX_COLOR_RE.match(config.background_color or ""):
        errors.append(f"background_color 형식이 올바르지 않습니다: {config.background_color} (예: #FFFFFF)")

    # display 모드 검증
    if config.display not in _VALID_DISPLAYS:
        errors.append(f"display는 {_VALID_DISPLAYS} 중 하나여야 합니다: {config.display}")

    # 아이콘 검증
    if not config.icons:
        errors.append("최소 1개의 아이콘이 필요합니다")
    else:
        for i, icon in enumerate(config.icons):
            if "src" not in icon:
                errors.append(f"아이콘[{i}]에 src가 없습니다")
            if "sizes" not in icon:
                errors.append(f"아이콘[{i}]에 sizes가 없습니다")

    return errors


def generate_install_prompt(config: PWAConfig) -> dict:
    """설치 프롬프트 메타데이터를 생성한다."""
    return {
        "app_name": config.app_name,
        "short_name": config.short_name,
        "description": f"{config.app_name} 앱을 설치하시겠습니까?",
        "install_button_text": "설치",
        "dismiss_button_text": "나중에",
        "icon": config.icons[0] if config.icons else None,
        "display": config.display,
    }
