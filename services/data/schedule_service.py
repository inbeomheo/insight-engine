"""
예약 발행 서비스

Supabase 활성화 시 DB 사용, 비활성화 시 메모리 딕셔너리 fallback.
"""
import uuid
from datetime import datetime, timezone

from services.core.logging_config import get_logger
from services.data.supabase_service import get_supabase, is_supabase_enabled
import logging

logger = get_logger('schedule_service')

# 메모리 fallback 저장소
_memory_store: dict[str, dict] = {}


class ScheduleService:
    """예약 발행 CRUD 서비스"""

    def create(self, user_id: str, title: str, content: str, html: str | None,
               target_plugin: str, scheduled_at: str) -> dict | None:
        """예약 생성

        Args:
            scheduled_at: ISO 8601 형식 문자열

        Returns:
            생성된 예약 dict 또는 None
        """
        if is_supabase_enabled():
            return self._db_create(user_id, title, content, html, target_plugin, scheduled_at)

        try:
            # scheduled_at ISO 8601 유효성 검증 (잘못된 값이면 get_due_posts에서 크래시)
            try:
                datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                logger.error("잘못된 scheduled_at 형식: %s", scheduled_at)
                return {}

            # 메모리 fallback
            post_id = str(uuid.uuid4())
            post = {
                'id': post_id,
                'user_id': user_id,
                'title': title,
                'content': content,
                'html': html,
                'target_plugin': target_plugin,
                'scheduled_at': scheduled_at,
                'status': 'pending',
                'error_message': None,
                'published_url': None,
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
            _memory_store[post_id] = post
            return post
        except Exception as e:
            logger.error("create 실패: %s", e, exc_info=True)
            return {}

    def list_by_user(self, user_id: str) -> list[dict]:
        """사용자의 예약 목록 조회 (최신순)"""
        if is_supabase_enabled():
            return self._db_list_by_user(user_id)

        try:
            return sorted(
                [p for p in _memory_store.values() if p['user_id'] == user_id],
                key=lambda p: p['created_at'],
                reverse=True,
            )
        except Exception as e:
            logger.error("list_by_user 실패: %s", e, exc_info=True)
            return []

    def delete(self, post_id: str, user_id: str) -> bool:
        """예약 삭제 (본인 것만)"""
        if is_supabase_enabled():
            return self._db_delete(post_id, user_id)

        try:
            post = _memory_store.get(post_id)
            if post and post['user_id'] == user_id:
                del _memory_store[post_id]
                return True
            return False
        except Exception as e:
            logger.error("delete 실패: %s", e, exc_info=True)
            return False

    def get_due_posts(self) -> list[dict]:
        """발행 시각이 지난 pending 포스트 조회"""
        try:
            now = datetime.now(timezone.utc)

            if is_supabase_enabled():
                return self._db_get_due_posts(now)

            return [
                p for p in _memory_store.values()
                if p['status'] == 'pending'
                and datetime.fromisoformat(p['scheduled_at'].replace('Z', '+00:00')) <= now
            ]
        except Exception as e:
            logger.error("get_due_posts 실패: %s", e, exc_info=True)
            return []

    def update_status(self, post_id: str, status: str,
                      error_message: str | None = None,
                      published_url: str | None = None) -> None:
        """예약 상태 업데이트"""
        try:
            if is_supabase_enabled():
                self._db_update_status(post_id, status, error_message, published_url)
                return

            post = _memory_store.get(post_id)
            if post:
                post['status'] = status
                if error_message is not None:
                    post['error_message'] = error_message
                if published_url is not None:
                    post['published_url'] = published_url
        except Exception as e:
            logger.error("update_status 실패: %s", e, exc_info=True)
            return None

    # --- Supabase DB 구현 ---

    def _db_create(self, user_id, title, content, html, target_plugin, scheduled_at):
        try:
            supabase = get_supabase()
            result = supabase.table('ie_scheduled_posts').insert({
                'user_id': user_id,
                'title': title,
                'content': content,
                'html': html,
                'target_plugin': target_plugin,
                'scheduled_at': scheduled_at,
            }).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"예약 생성 실패: {e}")
            return None

    def _db_list_by_user(self, user_id):
        try:
            supabase = get_supabase()
            result = supabase.table('ie_scheduled_posts') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"예약 목록 조회 실패: {e}")
            return []

    def _db_delete(self, post_id, user_id):
        try:
            supabase = get_supabase()
            supabase.table('ie_scheduled_posts') \
                .delete() \
                .eq('id', post_id) \
                .eq('user_id', user_id) \
                .execute()
            return True
        except Exception as e:
            logger.error(f"예약 삭제 실패: {e}")
            return False

    def _db_get_due_posts(self, now):
        try:
            supabase = get_supabase()
            result = supabase.table('ie_scheduled_posts') \
                .select('*') \
                .eq('status', 'pending') \
                .lte('scheduled_at', now.isoformat()) \
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"예약 조회 실패: {e}")
            return []

    def _db_update_status(self, post_id, status, error_message, published_url):
        try:
            supabase = get_supabase()
            updates = {'status': status}
            if error_message is not None:
                updates['error_message'] = error_message
            if published_url is not None:
                updates['published_url'] = published_url
            supabase.table('ie_scheduled_posts') \
                .update(updates) \
                .eq('id', post_id) \
                .execute()
        except Exception as e:
            logger.error(f"예약 상태 업데이트 실패: {e}")


# 싱글턴 인스턴스
schedule_service = ScheduleService()
