"""
화이트라벨 서비스 (F4-15)
커스텀 브랜딩 (로고, 색상, 도메인)
"""
from datetime import datetime, timezone
from services.logging_config import ServiceLogger

logger = ServiceLogger('WhitelabelService')

# 기본 브랜딩
DEFAULT_BRANDING = {
    'app_name': 'Insight Engine',
    'logo_url': '',
    'primary_color': '#6366f1',
    'accent_color': '#8b5cf6',
    'favicon_url': '',
    'custom_domain': '',
    'footer_text': '',
}


class WhitelabelService:
    """화이트라벨 커스텀 브랜딩 관리"""

    def __init__(self):
        # workspace_id → 브랜딩 설정
        self._brands: dict[str, dict] = {}

    def set_branding(self, workspace_id: str, branding: dict) -> dict:
        """브랜딩 설정 업데이트"""
        current = self._brands.get(workspace_id, {**DEFAULT_BRANDING})

        # 허용된 키만 업데이트
        allowed_keys = set(DEFAULT_BRANDING.keys())
        for key, value in branding.items():
            if key in allowed_keys:
                current[key] = value

        current['updated_at'] = datetime.now(timezone.utc).isoformat()
        self._brands[workspace_id] = current
        logger.info(f"브랜딩 업데이트: {workspace_id}")
        return current

    def get_branding(self, workspace_id: str) -> dict:
        """브랜딩 설정 조회 (없으면 기본값)"""
        return self._brands.get(workspace_id, {**DEFAULT_BRANDING})

    def reset_branding(self, workspace_id: str) -> dict:
        """기본 브랜딩으로 초기화"""
        self._brands[workspace_id] = {**DEFAULT_BRANDING}
        return self._brands[workspace_id]

    def validate_domain(self, domain: str) -> dict:
        """커스텀 도메인 유효성 검증 (기본 형식 체크)"""
        if not domain:
            return {'valid': False, 'reason': '도메인이 비어있습니다.'}

        # 간단한 형식 검증
        parts = domain.split('.')
        if len(parts) < 2:
            return {'valid': False, 'reason': '올바른 도메인 형식이 아닙니다.'}

        # 이미 사용 중인지 확인
        for ws_id, brand in self._brands.items():
            if brand.get('custom_domain') == domain:
                return {'valid': False, 'reason': '이미 사용 중인 도메인입니다.'}

        return {'valid': True, 'domain': domain}


whitelabel_service = WhitelabelService()
