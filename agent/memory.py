"""
에이전트 메모리 시스템 — SQLite WAL + 동결 스냅샷

Hermes Agent 패턴:
- 세션 시작 시 메모리를 시스템 프롬프트에 주입 (동결)
- 세션 중 도구로 디스크 갱신하지만 시스템 프롬프트는 불변 (프롬프트 캐시 보존)
- SQLite WAL 모드 + FTS5 풀텍스트 검색
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from utils.runtime_paths import app_data_path

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = app_data_path("agent_state.db")


@dataclass
class Session:
    """에이전트 세션."""
    session_id: str
    user_id: Optional[str]
    model: str
    system_prompt_snapshot: str
    created_at: float
    updated_at: float
    metadata: Dict[str, Any]


@dataclass
class MemoryEntry:
    """메모리 항목."""
    key: str
    value: str
    category: str  # "agent" | "user" | "project"
    updated_at: float


class AgentMemoryStore:
    """SQLite 기반 에이전트 상태 저장소.

    3계층 메모리:
    1. agent_memory — 에이전트가 학습한 환경 사실, 도구 특이점
    2. user_memory — 사용자 선호도, 커뮤니케이션 스타일
    3. project_memory — 프로젝트 컨벤션, 코드 패턴

    동결 스냅샷:
    - create_session() 시점에 메모리를 시스템 프롬프트에 주입
    - 세션 중 update_memory()로 디스크는 갱신하지만
    - get_session()의 system_prompt_snapshot은 불변
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.environ.get("AGENT_DB_PATH") or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """데이터베이스 테이블 초기화."""
        with self._conn() as conn:
            conn.executescript("""
                PRAGMA journal_mode = WAL;
                PRAGMA synchronous = NORMAL;

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    model TEXT NOT NULL,
                    system_prompt_snapshot TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    metadata TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT,
                    tool_call_id TEXT,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );
                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id, created_at);

                CREATE TABLE IF NOT EXISTS memory (
                    key TEXT NOT NULL,
                    category TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (key, category)
                );

                CREATE TABLE IF NOT EXISTS tool_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    args TEXT,
                    result_summary TEXT,
                    elapsed_ms INTEGER,
                    success INTEGER DEFAULT 1,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tool_usage_session
                    ON tool_usage(session_id, created_at);
            """)

            # FTS5 가상 테이블 (풀텍스트 검색)
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts
                    USING fts5(key, value, category, content=memory, content_rowid=rowid);
                """)
            except sqlite3.OperationalError:
                # FTS5 미지원 환경 (드묾)
                logger.warning("FTS5 미지원 — 풀텍스트 검색 비활성화")

    @contextmanager
    def _conn(self):
        """SQLite 연결 컨텍스트 매니저."""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── 세션 관리 ──

    def create_session(
        self,
        model: str,
        base_system_prompt: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """새 세션을 생성하고 메모리를 동결합니다.

        Args:
            model: 사용할 AI 모델 ID
            base_system_prompt: 기본 시스템 프롬프트
            user_id: 사용자 ID (옵션)
            metadata: 추가 메타데이터

        Returns:
            생성된 Session (system_prompt_snapshot에 메모리 주입 완료)
        """
        session_id = str(uuid.uuid4())
        now = time.time()

        # 동결 스냅샷: 현재 메모리를 시스템 프롬프트에 주입
        memory_block = self._build_memory_block(user_id)
        snapshot = base_system_prompt
        if memory_block:
            snapshot = f"{base_system_prompt}\n\n{memory_block}"

        meta = metadata or {}
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, user_id, model, system_prompt_snapshot, "
                "created_at, updated_at, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session_id, user_id, model, snapshot, now, now, json.dumps(meta)),
            )

        logger.info("세션 생성: %s (model=%s, user=%s)", session_id[:8], model, user_id)
        return Session(
            session_id=session_id,
            user_id=user_id,
            model=model,
            system_prompt_snapshot=snapshot,
            created_at=now,
            updated_at=now,
            metadata=meta,
        )

    def get_session(self, session_id: str) -> Optional[Session]:
        """세션 조회 (동결 스냅샷 포함)."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()

        if not row:
            return None

        return Session(
            session_id=row["session_id"],
            user_id=row["user_id"],
            model=row["model"],
            system_prompt_snapshot=row["system_prompt_snapshot"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=json.loads(row["metadata"]),
        )

    def list_sessions(
        self, user_id: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """세션 목록 조회 (최근순)."""
        with self._conn() as conn:
            if user_id:
                rows = conn.execute(
                    "SELECT session_id, user_id, model, created_at, updated_at, metadata "
                    "FROM sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT session_id, user_id, model, created_at, updated_at, metadata "
                    "FROM sessions ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()

        return [dict(r) for r in rows]

    # ── 메시지 히스토리 ──

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
        tool_call_id: Optional[str] = None,
    ) -> None:
        """세션에 메시지 추가."""
        now = time.time()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, tool_calls, "
                "tool_call_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session_id, role, content,
                    json.dumps(tool_calls) if tool_calls else None,
                    tool_call_id, now,
                ),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )

    def get_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """세션 메시지 히스토리 조회."""
        with self._conn() as conn:
            query = (
                "SELECT role, content, tool_calls, tool_call_id, created_at "
                "FROM messages WHERE session_id = ? ORDER BY created_at ASC"
            )
            params: list = [session_id]
            if limit:
                query += " LIMIT ?"
                params.append(limit)

            rows = conn.execute(query, params).fetchall()

        messages = []
        for r in rows:
            msg: Dict[str, Any] = {"role": r["role"], "content": r["content"]}
            if r["tool_calls"]:
                msg["tool_calls"] = json.loads(r["tool_calls"])
            if r["tool_call_id"]:
                msg["tool_call_id"] = r["tool_call_id"]
            messages.append(msg)
        return messages

    # ── 메모리 (3계층) ──

    def update_memory(self, key: str, value: str, category: str = "agent") -> None:
        """메모리 항목 갱신 (디스크에 저장, 현재 세션 프롬프트에는 미반영).

        Args:
            key: 메모리 키 (예: "preferred_language")
            value: 메모리 값
            category: "agent" | "user" | "project"
        """
        now = time.time()
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO memory (key, category, value, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (key, category, value, now),
            )
        logger.debug("메모리 갱신: [%s] %s", category, key)

    def get_memory(self, key: str, category: str = "agent") -> Optional[str]:
        """메모리 항목 조회."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM memory WHERE key = ? AND category = ?",
                (key, category),
            ).fetchone()
        return row["value"] if row else None

    def list_memory(self, category: Optional[str] = None) -> List[MemoryEntry]:
        """메모리 항목 목록."""
        with self._conn() as conn:
            if category:
                rows = conn.execute(
                    "SELECT * FROM memory WHERE category = ? ORDER BY updated_at DESC",
                    (category,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memory ORDER BY category, updated_at DESC"
                ).fetchall()

        return [
            MemoryEntry(
                key=r["key"], value=r["value"],
                category=r["category"], updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def search_memory(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """풀텍스트 메모리 검색 (FTS5)."""
        with self._conn() as conn:
            try:
                rows = conn.execute(
                    "SELECT m.key, m.value, m.category, m.updated_at "
                    "FROM memory_fts f JOIN memory m ON f.rowid = m.rowid "
                    "WHERE memory_fts MATCH ? LIMIT ?",
                    (query, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                # FTS5 없으면 LIKE 폴백
                rows = conn.execute(
                    "SELECT * FROM memory WHERE value LIKE ? LIMIT ?",
                    (f"%{query}%", limit),
                ).fetchall()

        return [
            MemoryEntry(
                key=r["key"], value=r["value"],
                category=r["category"], updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def delete_memory(self, key: str, category: str = "agent") -> bool:
        """메모리 항목 삭제."""
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM memory WHERE key = ? AND category = ?",
                (key, category),
            )
        return cursor.rowcount > 0

    # ── 도구 사용 기록 ──

    def log_tool_usage(
        self,
        session_id: str,
        tool_name: str,
        args: Optional[Dict] = None,
        result_summary: Optional[str] = None,
        elapsed_ms: Optional[int] = None,
        success: bool = True,
    ) -> None:
        """도구 사용 기록 저장."""
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO tool_usage (session_id, tool_name, args, result_summary, "
                "elapsed_ms, success, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session_id, tool_name,
                    json.dumps(args) if args else None,
                    result_summary[:500] if result_summary else None,
                    elapsed_ms, 1 if success else 0, time.time(),
                ),
            )

    # ── 내부 헬퍼 ──

    def _build_memory_block(self, user_id: Optional[str] = None) -> str:
        """메모리를 시스템 프롬프트 블록으로 포맷합니다."""
        sections = []

        # 에이전트 메모리
        agent_mem = self.list_memory(category="agent")
        if agent_mem:
            lines = [f"- {m.key}: {m.value}" for m in agent_mem[:20]]
            sections.append(f"## Agent Memory\n" + "\n".join(lines))

        # 프로젝트 메모리
        project_mem = self.list_memory(category="project")
        if project_mem:
            lines = [f"- {m.key}: {m.value}" for m in project_mem[:20]]
            sections.append(f"## Project Memory\n" + "\n".join(lines))

        # 사용자 메모리
        if user_id:
            user_mem = [m for m in self.list_memory(category="user") if user_id in m.key]
            if user_mem:
                lines = [f"- {m.key.replace(user_id + ':', '')}: {m.value}" for m in user_mem[:10]]
                sections.append(f"## User Preferences\n" + "\n".join(lines))

        if not sections:
            return ""

        return "<memory>\n" + "\n\n".join(sections) + "\n</memory>"


# 기본 인스턴스
memory_store = AgentMemoryStore()
