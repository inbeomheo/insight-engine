"""
CMS 통합 허브 (F7-23)

하나의 API 호출로 여러 CMS/플랫폼에 동시에 콘텐츠를 발행합니다.
plugin_registry에 등록된 플러그인을 사용합니다.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

logger = logging.getLogger(__name__)

_MAX_WORKERS = 6


class CMSHub:
    """다중 CMS 동시 발행 허브"""

    def publish_to_all(
        self,
        plugin_ids: list[str],
        title: str,
        content: str,
        plugin_configs: Optional[dict] = None,
    ) -> dict:
        """여러 플러그인에 동시 발행

        Args:
            plugin_ids: 발행할 플러그인 ID 목록
            title: 콘텐츠 제목
            content: 콘텐츠 본문
            plugin_configs: 플러그인별 설정 dict
                            {"plugin_id": {"param": "value", ...}}

        Returns:
            {
                "total": int,
                "success": int,
                "failed": int,
                "results": {"plugin_id": {"success": bool, "message": str, "url": str | None}}
            }
        """
        from .registry import plugin_registry

        if not plugin_ids:
            return {'total': 0, 'success': 0, 'failed': 0, 'results': {}}

        configs = plugin_configs or {}
        results = {}
        workers = min(_MAX_WORKERS, len(plugin_ids))

        def _publish_one(plugin_id: str) -> tuple[str, dict]:
            plugin = plugin_registry.get(plugin_id)
            if plugin is None:
                return plugin_id, {
                    'success': False,
                    'message': f"플러그인 '{plugin_id}'을(를) 찾을 수 없습니다.",
                    'url': None,
                }
            try:
                kwargs = configs.get(plugin_id, {})
                result = plugin.execute(content, title, **kwargs)
                return plugin_id, result
            except Exception as e:
                logger.error(f"CMS Hub [{plugin_id}] 발행 오류: {e}")
                return plugin_id, {
                    'success': False,
                    'message': f'발행 중 오류: {str(e)}',
                    'url': None,
                }

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_publish_one, pid): pid for pid in plugin_ids}
            for future in as_completed(futures):
                pid, result = future.result()
                results[pid] = result

        success_count = sum(1 for r in results.values() if r.get('success'))
        return {
            'total': len(plugin_ids),
            'success': success_count,
            'failed': len(plugin_ids) - success_count,
            'results': results,
        }

    def get_available_plugins(self) -> list[dict]:
        """사용 가능한 플러그인 목록 반환"""
        from .registry import plugin_registry
        return plugin_registry.list_plugins()

    def validate_plugin_config(self, plugin_id: str, config: dict) -> dict:
        """플러그인 설정 유효성 검사

        Returns:
            {"valid": bool, "errors": [str]}
        """
        from .registry import plugin_registry

        plugin = plugin_registry.get(plugin_id)
        if plugin is None:
            return {'valid': False, 'errors': [f"플러그인 '{plugin_id}'을(를) 찾을 수 없습니다."]}

        schema = plugin.schema()
        required = schema.get('required', [])
        errors = []

        for field in required:
            if not config.get(field):
                errors.append(f"'{field}' 설정이 필요합니다.")

        return {'valid': len(errors) == 0, 'errors': errors}


cms_hub = CMSHub()
