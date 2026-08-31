"""
AI 결과 캐시 서비스
SQLite 기반, TTL + LRU eviction 지원
"""
import hashlib
import json
import os
import random
import sqlite3
import threading
import time
from typing import Any, Dict, Optional

_local = threading.local()


class AICacheService:
    """SQLite 기반 AI 생성 결과 캐시"""

    def __init__(self, db_path: str, ttl_days: int = 30, max_size_mb: int = 512) -> None:
        self.db_path = db_path
        self.ttl_seconds = ttl_days * 86400
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._hits = 0
        self._misses = 0

        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """스레드별 + 인스턴스별 연결을 캐싱하여 매 요청마다 connect() 호출 방지.

        db_path 해시 기반 키를 사용하여 id() 재사용으로 인한 stale 연결 문제를 방지한다.
        """
        attr = f'conn_{hashlib.md5(self.db_path.encode()).hexdigest()}'
        conn = getattr(_local, attr, None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, timeout=5.0, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            setattr(_local, attr, conn)
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
    def make_key(
        video_id: str,
        style_id: str,
        model: str,
        length: str = 'medium',
        writing_style: str = 'conversational',
        transcript_language: Optional[str] = None,
        enable_citations: bool = False,
        *,
        custom_prompt: Optional[str] = None,
        detail_level: Optional[str] = None,
        web_search: bool = False,
        output_format: str = 'html',
        max_chars: Optional[int] = None,
        analyze: bool = False,
        language: Optional[str] = None,
        modifiers: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        rag_scope: Optional[str] = None,
    ) -> str:
        """생성 조건 fingerprint를 canonical JSON으로 해시한 캐시 키.

        원문 커스텀 프롬프트는 키에 넣지 않고 SHA256 해시만 포함한다.
        """
        mods = modifiers if isinstance(modifiers, dict) else {}
        prompt_hash = ''
        if custom_prompt:
            prompt_hash = hashlib.sha256(str(custom_prompt).encode('utf-8')).hexdigest()
        # 커스텀 프롬프트/RAG는 사용자 캐시, 기본 공개 결과는 글로벌 캐시
        user_scope = (user_id or '') if (prompt_hash or rag_scope) else ''
        fingerprint = {
            'v': 2,
            'video_id': video_id,
            'style_id': style_id,
            'model': model,
            'length': length or 'medium',
            'writing_style': writing_style or 'conversational',
            'transcript_language': transcript_language or '',
            'enable_citations': bool(enable_citations),
            'custom_prompt_hash': prompt_hash,
            'detail_level': detail_level or 'standard',
            'web_search': bool(web_search),
            'output_format': output_format or 'html',
            'max_chars': int(max_chars) if max_chars else 0,
            'analyze': bool(analyze),
            'language': language or mods.get('language') or '',
            'modifiers': {
                'length': mods.get('length', length or 'medium'),
                'writing_style': mods.get('writing_style', writing_style or 'conversational'),
                'language': mods.get('language') or language or '',
            },
            'user_scope': user_scope,
            'rag_scope': rag_scope or '',
        }
        raw = json.dumps(fingerprint, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """캐시에서 결과 조회. TTL 만료 시 None 반환.

        약 2% 확률로 만료 항목 일괄 정리를 수행하여
        별도 스케줄러 없이도 디스크 공간을 회수합니다.
        """
        # 확률적 만료 정리 (약 50회 조회당 1회)
        if random.random() < 0.02:
            self.purge_expired()

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
            usage_percent = round(row['total_bytes'] / self.max_size_bytes * 100, 1) if self.max_size_bytes > 0 else 0.0

            return {
                'count': count,
                'total_bytes': row['total_bytes'],
                'total_mb': round(row['total_bytes'] / (1024 * 1024), 2),
                'avg_entry_size_kb': avg_entry_size_kb,
                'max_mb': self.max_size_bytes // (1024 * 1024),
                'usage_percent': usage_percent,
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
                cursor = conn.execute("DELETE FROM ai_cache WHERE 1=1")
            return cursor.rowcount

    def purge_expired(self) -> int:
        """만료된 항목 정리"""
        cutoff = time.time() - self.ttl_seconds
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM ai_cache WHERE created_at < ?", (cutoff,))
            return cursor.rowcount
