"""
감사 로그 서비스 (F4-25)
사용자 행동 기록 + 조회
"""
import uuid
from datetime import datetime, timezone
from services.core.logging_config import ServiceLogger
import logging

logger = ServiceLogger('AuditLogService')


class AuditLogService:
    """감사 로그 CRUD"""

    def __init__(self, max_entries: int = 10000):
        self._logs: list[dict] = []
        self._max_entries = max_entries

    def log(
        self,
        user_id: str,
        action: str,
        resource_type: str = '',
        resource_id: str = '',
        details: dict | None = None,
        ip_address: str = '',
    ) -> dict:
        """감사 로그 기록"""
        try:
            entry = {
                'id': uuid.uuid4().hex[:12],
                'user_id': user_id,
                'action': action,
                'resource_type': resource_type,
                'resource_id': resource_id,
                'details': details or {},
                'ip_address': ip_address,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }

            self._logs.append(entry)

            # 최대 크기 초과 시 오래된 로그 제거
            if len(self._logs) > self._max_entries:
                self._logs = self._logs[-self._max_entries:]

            return entry
        except Exception as e:
            logger.error("log 실패: %s", e, exc_info=True)
            return {}

    def query(
        self,
        user_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """감사 로그 조회 (필터링)"""
        try:
            results = self._logs

            if user_id:
                results = [l for l in results if l['user_id'] == user_id]
            if action:
                results = [l for l in results if l['action'] == action]
            if resource_type:
                results = [l for l in results if l['resource_type'] == resource_type]

            # 최신순 정렬
            results = sorted(results, key=lambda l: l['timestamp'], reverse=True)
            return results[offset:offset + limit]
        except Exception as e:
            logger.error("query 실패: %s", e, exc_info=True)
            return []

    def get_actions_summary(self, user_id: str | None = None) -> dict[str, int]:
        """행동별 횟수 집계"""
        try:
            target = self._logs if not user_id else [l for l in self._logs if l['user_id'] == user_id]
            summary: dict[str, int] = {}
            for entry in target:
                action = entry['action']
                summary[action] = summary.get(action, 0) + 1
            return summary
        except Exception as e:
            logger.error("get_actions_summary 실패: %s", e, exc_info=True)
            return {}

    def clear_old_logs(self, days: int = 90) -> int:
        """오래된 로그 삭제"""
        try:
            cutoff = datetime.now(timezone.utc) - __import__('datetime').timedelta(days=days)
            before = len(self._logs)
            self._logs = [
                l for l in self._logs
                if datetime.fromisoformat(l['timestamp']) > cutoff
            ]
            removed = before - len(self._logs)
            if removed:
                logger.info(f"감사 로그 정리: {removed}건 삭제")
            return removed
        except Exception as e:
            logger.error("clear_old_logs 실패: %s", e, exc_info=True)
            return 0


audit_log_service = AuditLogService()
