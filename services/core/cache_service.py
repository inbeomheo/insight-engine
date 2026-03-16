"""
AI 결과 캐시 서비스
SQLite 기반, TTL + LRU eviction 지원
"""
import hashlib
import json
import os
import sqlite3
import time
from typing import Any, Dict, Optional


class AICacheService:
    """SQLite 기반 AI 생성 결과 캐시"""

    def __init__(self, db_path: str, ttl_days: int = 30, max_size_mb: int = 512) -> None:
        self.db_path = db_path
        self.ttl_seconds = ttl_days * 86400
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._hits = 0
        self._misses = 0

        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_cache (
                    cache_key TEXT PRIMARY KEY,
                    video_id TEXT NOT NULL,
                    style_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    length TEXT,
                    writing_style TEXT,
                    result_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    accessed_at REAL NOT NULL,
                    size_bytes INTEGER NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_cache_video ON ai_cache(video_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_cache_accessed ON ai_cache(accessed_at)")

    @staticmethod
    def make_key(video_id: str, style_id: str, model: str, length: str = 'medium', writing_style: str = 'conversational') -> str:
        """캐시 키 생성 (SHA256)"""
        raw = f"{video_id}|{style_id}|{model}|{length}|{writing_style}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """캐시에서 결과 조회. TTL 만료 시 None 반환."""
        now = time.time()
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT result_json, created_at FROM ai_cache WHERE cache_key = ?",
                (cache_key,)
            ).fetchone()

            if not row:
                self._misses += 1
                return None

            # TTL 체크
            if now - row['created_at'] > self.ttl_seconds:
                conn.execute("DELETE FROM ai_cache WHERE cache_key = ?", (cache_key,))
                self._misses += 1
                return None

            # accessed_at 갱신
            conn.execute(
                "UPDATE ai_cache SET accessed_at = ? WHERE cache_key = ?",
                (now, cache_key)
            )
            self._hits += 1
            result = json.loads(row['result_json'])
            result['_cached_at'] = row['created_at']
            return result

    def put(self, cache_key: str, video_id: str, style_id: str, model: str, length: str, writing_style: str, result: Dict[str, Any]) -> None:
        """캐시에 결과 저장. 용량 초과 시 LRU eviction."""
        now = time.time()
        result_json = json.dumps(result, ensure_ascii=False)
        size_bytes = len(result_json.encode('utf-8'))

        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ai_cache
                (cache_key, video_id, style_id, model, length, writing_style,
                 result_json, created_at, accessed_at, size_bytes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cache_key, video_id, style_id, model, length, writing_style,
                  result_json, now, now, size_bytes))

            # 동일 연결 내에서 eviction 수행 (불필요한 연결 재생성 방지)
            self._evict_if_needed(conn)

    def _evict_if_needed(self, conn: Optional['sqlite3.Connection'] = None) -> None:
        """총 용량이 max_size_bytes 초과 시 오래된 항목 20% 삭제"""
        own_conn = conn is None
        if own_conn:
            conn = self._get_conn()
        try:
            total = conn.execute("SELECT COALESCE(SUM(size_bytes), 0) AS total FROM ai_cache").fetchone()['total']
            if total <= self.max_size_bytes:
                return

            count = conn.execute("SELECT COUNT(*) AS cnt FROM ai_cache").fetchone()['cnt']
            delete_count = max(1, count // 5)  # 20%
            conn.execute("""
                DELETE FROM ai_cache WHERE cache_key IN (
                    SELECT cache_key FROM ai_cache ORDER BY accessed_at ASC LIMIT ?
                )
            """, (delete_count,))
            if own_conn:
                conn.commit()
        finally:
            if own_conn:
                conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        from datetime import datetime, timezone
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT COUNT(*) AS count,
                       COALESCE(SUM(size_bytes), 0) AS total_bytes,
                       MIN(created_at) AS oldest_ts,
                       MAX(created_at) AS newest_ts
                FROM ai_cache
            """).fetchone()
            total_requests = self._hits + self._misses
            hit_rate = round(self._hits / total_requests, 4) if total_requests > 0 else 0.0

            oldest_entry = None
            newest_entry = None
            if row['oldest_ts'] is not None:
                oldest_entry = datetime.fromtimestamp(row['oldest_ts'], tz=timezone.utc).isoformat()
            if row['newest_ts'] is not None:
                newest_entry = datetime.fromtimestamp(row['newest_ts'], tz=timezone.utc).isoformat()

            count = row['count']
            avg_entry_size_kb = round(row['total_bytes'] / count / 1024, 2) if count > 0 else 0.0

            return {
                'count': count,
                'total_bytes': row['total_bytes'],
                'total_mb': round(row['total_bytes'] / (1024 * 1024), 2),
                'avg_entry_size_kb': avg_entry_size_kb,
                'max_mb': self.max_size_bytes // (1024 * 1024),
                'ttl_days': self.ttl_seconds // 86400,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'oldest_entry': oldest_entry,
                'newest_entry': newest_entry,
            }

    def clear(self, video_id: Optional[str] = None) -> int:
        """캐시 삭제. video_id 지정 시 해당 영상만."""
        with self._get_conn() as conn:
            if video_id:
                cursor = conn.execute("DELETE FROM ai_cache WHERE video_id = ?", (video_id,))
            else:
                cursor = conn.execute("DELETE FROM ai_cache")
            return cursor.rowcount

    def purge_expired(self) -> int:
        """만료된 항목 정리"""
        cutoff = time.time() - self.ttl_seconds
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM ai_cache WHERE created_at < ?", (cutoff,))
            return cursor.rowcount
