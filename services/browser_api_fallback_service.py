"""
브라우저 API 폴백 서비스 — 브라우저 API 가용성 확인 + 폴백 전략
"""

from dataclasses import dataclass, field

# 폴백 매핑 테이블
FALLBACK_MAP = {
    "IntersectionObserver": "scroll event listener",
    "ResizeObserver": "window resize event",
    "MutationObserver": "polling with setInterval",
    "fetch": "XMLHttpRequest",
    "Promise": "callback pattern",
    "WebSocket": "long polling",
    "ServiceWorker": "AppCache",
    "IndexedDB": "localStorage",
    "WebGL": "Canvas 2D",
    "WebRTC": "WebSocket streaming",
    "SharedWorker": "BroadcastChannel",
    "BroadcastChannel": "postMessage",
    "Clipboard": "document.execCommand('copy')",
    "Notification": "in-app notification banner",
    "Geolocation": "IP-based location",
    "WebAssembly": "JavaScript fallback",
    "CustomElements": "polyfill (webcomponents.js)",
    "ShadowDOM": "CSS scoping",
}

# 폴리필 가능 API 목록
POLYFILL_AVAILABLE = {
    "IntersectionObserver", "ResizeObserver", "fetch", "Promise",
    "CustomElements", "ShadowDOM", "URLSearchParams", "AbortController",
    "Array.from", "Object.assign", "Symbol",
}


@dataclass
class APICapability:
    """API 가용성 정보"""
    api_name: str
    supported: bool
    fallback: str  # None이면 대안 없음
    polyfill_available: bool


@dataclass
class CompatibilityReport:
    """호환성 보고서"""
    capabilities: list  # list[APICapability]
    supported_count: int
    total_count: int
    score: float  # 0.0 ~ 1.0


def check_capabilities(required_apis: list, available_apis: list) -> CompatibilityReport:
    """필요 API의 가용성 확인"""
    available_set = set(available_apis)
    capabilities = []

    for api in required_apis:
        supported = api in available_set
        fallback = FALLBACK_MAP.get(api)
        polyfill = api in POLYFILL_AVAILABLE

        capabilities.append(APICapability(
            api_name=api,
            supported=supported,
            fallback=fallback,
            polyfill_available=polyfill,
        ))

    supported_count = sum(1 for c in capabilities if c.supported)
    total = len(capabilities)
    score = supported_count / total if total > 0 else 1.0

    return CompatibilityReport(
        capabilities=capabilities,
        supported_count=supported_count,
        total_count=total,
        score=score,
    )


def suggest_fallback(api_name: str) -> str:
    """폴백 API 제안 (없으면 None)"""
    return FALLBACK_MAP.get(api_name)


def generate_polyfill_list(report: CompatibilityReport) -> list:
    """필요 폴리필 목록 (미지원 + 폴리필 가능한 API)"""
    return [
        c.api_name for c in report.capabilities
        if not c.supported and c.polyfill_available
    ]


def calculate_compatibility_score(report: CompatibilityReport) -> float:
    """호환성 점수 (0~1)"""
    return report.score
