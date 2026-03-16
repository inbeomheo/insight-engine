"""
활동 피드 서비스 — 팀 활동 기록 및 조회
"""

import time
from dataclasses import dataclass, field, asdict
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ActivityItem:
    """활동 항목"""
    id: str
    workspace_id: str
    user_id: str
    user_email: Optional[str]
    action: str  # 'generated' | 'published' | 'commented' | 'approved' | 'scheduled'
    target_title: str
    target_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class ActivityFeedService:
    """인메모리 활동 피드 (워크스페이스별)"""

    MAX_ITEMS_PER_WORKSPACE = 200

    def __init__(self):
        # workspace_id -> list[ActivityItem] (최신 순)
        self._feeds: dict[str, list[ActivityItem]] = {}
        self._counter = 0

    def record(
        self,
        workspace_id: str,
        user_id: str,
        action: str,
        target_title: str,
        target_id: str | None = None,
        user_email: str | None = None,
        metadata: dict | None = None,
    ) -> ActivityItem:
        """활동 기록 추가"""
        try:
            self._counter += 1
            item = ActivityItem(
                id=f"act_{self._counter}_{int(time.time())}",
                workspace_id=workspace_id,
                user_id=user_id,
                user_email=user_email,
                action=action,
                target_title=target_title,
                target_id=target_id,
                metadata=metadata or {},
            )

            if workspace_id not in self._feeds:
                self._feeds[workspace_id] = []

            feed = self._feeds[workspace_id]
            feed.insert(0, item)

            # 최대 개수 제한
            if len(feed) > self.MAX_ITEMS_PER_WORKSPACE:
                self._feeds[workspace_id] = feed[:self.MAX_ITEMS_PER_WORKSPACE]

            return item
        except Exception as e:
            logger.error("record 실패: %s", e, exc_info=True)
            return None

    def get_feed(
        self,
        workspace_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """워크스페이스 활동 피드 조회"""
        try:
            feed = self._feeds.get(workspace_id, [])
            items = feed[offset:offset + limit]
            return [asdict(item) for item in items]
        except Exception as e:
            logger.error("get_feed 실패: %s", e, exc_info=True)
            return []

    def get_user_feed(
        self,
        user_id: str,
        limit: int = 30,
    ) -> list[dict]:
        """특정 사용자의 활동만 조회"""
        try:
            results = []
            for feed in self._feeds.values():
                for item in feed:
                    if item.user_id == user_id:
                        results.append(asdict(item))
                        if len(results) >= limit:
                            return results
            return results
        except Exception as e:
            logger.error("get_user_feed 실패: %s", e, exc_info=True)
            return []

    def clear_workspace(self, workspace_id: str) -> None:
        """워크스페이스 피드 초기화"""
        try:
            self._feeds.pop(workspace_id, None)
        except Exception as e:
            logger.error("clear_workspace 실패: %s", e, exc_info=True)
            return None


# 싱글턴 인스턴스
activity_feed_service = ActivityFeedService()
