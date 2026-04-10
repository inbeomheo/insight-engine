"""
RSS 피드 구독 관리 서비스

구독 목록을 JSON 파일로 관리하고,
새 글 감지 기능을 제공합니다.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional

import feedparser as _feedparser

from services.core.logging_config import get_logger
from services.platform.rss_service import parse_feed

logger = get_logger('rss_subscription')

# 구독 데이터 저장 경로
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
_SUBS_FILE = os.path.join(_DATA_DIR, 'rss_subscriptions.json')
_lock = Lock()


def _ensure_data_dir():
    """data 디렉토리가 없으면 생성합니다."""
    os.makedirs(_DATA_DIR, exist_ok=True)


def _load_all() -> Dict:
    """전체 구독 데이터를 로드합니다. {user_id: [subscription, ...]}"""
    if not os.path.exists(_SUBS_FILE):
        return {}
    try:
        with open(_SUBS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("구독 파일 로드 실패, 빈 데이터로 초기화")
        return {}


def _save_all(data: Dict):
    """전체 구독 데이터를 저장합니다."""
    _ensure_data_dir()
    with open(_SUBS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def subscribe(user_id: str, feed_url: str, title: str = '') -> Dict:
    """RSS 피드를 구독합니다.

    Args:
        user_id: 사용자 ID
        feed_url: RSS/Atom 피드 URL
        title: 피드 제목 (비어있으면 자동 감지 시도)

    Returns:
        생성된 구독 정보 딕셔너리

    Raises:
        ValueError: 유효하지 않은 피드 URL이거나 이미 구독 중
    """
    # 피드 유효성 검증 (실제 파싱 시도)
    try:
        parse_feed(feed_url, max_items=1)
    except Exception as e:
        raise ValueError(f"RSS 피드를 파싱할 수 없습니다: {e}")

    # 자동 제목 감지
    if not title:
        parsed = _feedparser.parse(feed_url)
        title = getattr(parsed.feed, 'title', '') or feed_url

    with _lock:
        data = _load_all()
        user_subs = data.get(user_id, [])

        # 중복 검사
        for sub in user_subs:
            if sub['feed_url'] == feed_url:
                raise ValueError("이미 구독 중인 피드입니다.")

        subscription = {
            'id': str(uuid.uuid4()),
            'feed_url': feed_url,
            'title': title,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'last_checked_at': None,
            'last_entry_url': None,
        }

        user_subs.append(subscription)
        data[user_id] = user_subs
        _save_all(data)

    logger.info(f"RSS 구독 추가: {title} ({feed_url}) - user={user_id}")
    return subscription


def unsubscribe(user_id: str, feed_id: str) -> bool:
    """RSS 구독을 해제합니다.

    Returns:
        성공 여부
    """
    try:
        with _lock:
            data = _load_all()
            user_subs = data.get(user_id, [])
            original_len = len(user_subs)
            user_subs = [s for s in user_subs if s['id'] != feed_id]

            if len(user_subs) == original_len:
                return False

            data[user_id] = user_subs
            _save_all(data)

        logger.info(f"RSS 구독 해제: {feed_id} - user={user_id}")
        return True
    except Exception as e:
        logger.error("unsubscribe 실패: %s", e, exc_info=True)
        return False


def list_subscriptions(user_id: str) -> List[Dict]:
    """사용자의 구독 목록을 반환합니다."""
    try:
        data = _load_all()
        return data.get(user_id, [])
    except Exception as e:
        logger.error("list_subscriptions 실패: %s", e, exc_info=True)
        return []


def check_new_entries(subscription: Dict) -> List[Dict]:
    """구독 피드에서 마지막 확인 이후 새 글을 감지합니다.

    Args:
        subscription: 구독 정보 딕셔너리

    Returns:
        새 엔트리 목록
    """
    feed_url = subscription['feed_url']
    last_entry_url = subscription.get('last_entry_url')

    try:
        entries = parse_feed(feed_url, max_items=20)
    except Exception as e:
        logger.error(f"피드 파싱 실패: {feed_url} - {e}")
        return []

    if not entries:
        return []

    # 처음 확인이면 최신 1개만 반환
    if last_entry_url is None:
        return entries[:1]

    # last_entry_url 이후의 새 글 수집
    new_entries = []
    for entry in entries:
        if entry.get('url') == last_entry_url:
            break
        new_entries.append(entry)

    return new_entries


def update_last_checked(user_id: str, feed_id: str, last_entry_url: Optional[str] = None) -> None:
    """구독의 마지막 확인 시간을 업데이트합니다."""
    try:
        with _lock:
            data = _load_all()
            user_subs = data.get(user_id, [])
            for sub in user_subs:
                if sub['id'] == feed_id:
                    sub['last_checked_at'] = datetime.now(timezone.utc).isoformat()
                    if last_entry_url:
                        sub['last_entry_url'] = last_entry_url
                    break
            data[user_id] = user_subs
            _save_all(data)
    except Exception as e:
        logger.error("update_last_checked 실패: %s", e, exc_info=True)
        return None


def check_all_subscriptions() -> List[Dict]:
    """모든 사용자의 모든 구독을 확인하고 새 글을 반환합니다.
    스케줄러 워커에서 호출됩니다.

    Returns:
        [{"user_id": str, "subscription": Dict, "new_entries": [Dict, ...]}]
    """
    try:
        data = _load_all()
        results = []

        for user_id, subs in data.items():
            for sub in subs:
                new_entries = check_new_entries(sub)
                if new_entries:
                    results.append({
                        'user_id': user_id,
                        'subscription': sub,
                        'new_entries': new_entries,
                    })
                    # 마지막 확인 업데이트
                    update_last_checked(
                        user_id, sub['id'],
                        last_entry_url=new_entries[0].get('url'),
                    )

        return results
    except Exception as e:
        logger.error("check_all_subscriptions 실패: %s", e, exc_info=True)
        return []
