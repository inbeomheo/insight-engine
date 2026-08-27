"""
Toolset 정의 — 도구 그룹핑 + 합성

Hermes 패턴: includes로 재귀적 Toolset 합성 가능.
20개 서비스 도메인 → 20개 Toolset + 역할별 합성 Toolset.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Set


# ── Toolset 정의 ──
# 각 Toolset은 {"tools": [...], "includes": [...]} 형태
# tools: 직접 포함하는 도구 이름 목록 (registry에서 조회)
# includes: 다른 Toolset을 재귀적으로 포함

TOOLSETS: Dict[str, Dict[str, list]] = {
    # ── 콘텐츠 수집 ──
    "collector": {
        "tools": [
            "collect_youtube", "collect_webpage", "collect_arxiv",
            "collect_rss", "collect_twitter", "collect_reddit",
            "collect_github", "collect_hackernews", "collect_podcast",
            "collect_stackoverflow", "detect_source_type",
        ],
        "includes": [],
        "description": "URL에서 콘텐츠를 수집하는 도구",
    },

    # ── 텍스트 분석 (88개 서비스) ──
    "analysis": {
        "tools": [],  # 동적 등록 (analysis_tools.py에서 자동)
        "includes": [],
        "description": "텍스트 가독성, 감정, 구조, 복잡도 등 85+ 분석 도구",
    },

    # ── SEO 최적화 (29개 서비스) ──
    "seo": {
        "tools": [],  # 동적 등록
        "includes": [],
        "description": "키워드, 메타데이터, 헤드라인, 링크, E-E-A-T 등 SEO 분석",
    },

    # ── 콘텐츠 생성/관리 (28개 서비스) ──
    "content": {
        "tools": [],  # 동적 등록
        "includes": [],
        "description": "아웃라인, FAQ, 브리프, 템플릿 등 콘텐츠 생성",
    },

    # ── AI 핵심 (ai_service, content_service) ──
    "core": {
        "tools": [
            "create_content", "create_content_stream",
            "extract_seo_metadata", "extract_geo_metadata",
            "get_transcript", "get_video_comments",
        ],
        "includes": [],
        "description": "AI 콘텐츠 생성 + YouTube 자막/댓글 추출",
    },

    # ── 품질 검증 (15개 서비스) ──
    "quality": {
        "tools": [],  # 동적 등록
        "includes": [],
        "description": "팩트체크, 표절, QA 게이트, 금칙어, 품질 평가",
    },

    # ── 미디어 생성 (16개 서비스) ──
    "media": {
        "tools": [],  # 동적 등록
        "includes": [],
        "description": "이미지, 썸네일, 인포그래픽, TTS, 비디오 생성",
    },

    # ── 자막/음성 (7개 서비스) ──
    "transcript": {
        "tools": [
            "transcribe_audio", "download_audio",
            "extract_subtitles", "split_chapters",
            "translate_transcript",
        ],
        "includes": [],
        "description": "Whisper 음성인식, 챕터 분할, 자막 번역",
    },

    # ── 외부 플랫폼 (12개 서비스) ──
    "platform": {
        "tools": [],  # 동적 등록
        "includes": [],
        "description": "GitHub, RSS, 소셜미디어 데이터 수집",
    },

    # ── RAG 지식 참조 (10개 서비스) ──
    "rag": {
        "tools": [
            "rag_query", "rag_upload", "rag_list_documents",
            "chunk_text",
        ],
        "includes": [],
        "description": "벡터 검색, 문서 업로드, 컨텍스트 빌드",
    },

    # ── 내보내기 (6개 서비스) ──
    "export": {
        "tools": [
            "export_docx", "export_markdown", "export_epub",
            "export_txt", "export_gdocs",
        ],
        "includes": [],
        "description": "DOCX, Markdown, EPUB, Google Docs 내보내기",
    },

    # ── 연동 서비스 (8개 서비스) ──
    "integrations": {
        "tools": [],  # 동적 등록
        "includes": [],
        "description": "Slack, Discord, Telegram, Airtable, Google Sheets 연동",
    },

    # ── MCP 플러그인 ──
    "mcp": {
        "tools": [
            "mcp_publish_naver", "mcp_publish_wordpress",
            "mcp_list_plugins",
        ],
        "includes": [],
        "description": "MCP 플러그인 발행 (Naver Blog, WordPress)",
    },

    # ── 예약/스케줄 ──
    "schedule": {
        "tools": [
            "create_schedule", "list_schedules",
            "cancel_schedule", "update_schedule",
        ],
        "includes": [],
        "description": "콘텐츠 예약 발행 관리",
    },

    # ── 에이전트 제어 ──
    "agent_control": {
        "tools": [
            "delegate_task", "memory_read", "memory_write",
            "memory_search", "clarify",
        ],
        "includes": [],
        "description": "서브에이전트 위임, 사용자별 격리 메모리 관리, 사용자 질문",
    },

    # ── 분석 대시보드 ──
    "analytics": {
        "tools": [
            "record_event", "get_dashboard_stats",
            "get_ab_test_results",
        ],
        "includes": [],
        "description": "이벤트 트래킹, A/B 테스트, 성과 대시보드",
    },

    # ── NotebookLM ──
    "notebooklm": {
        "tools": [
            "nlm_create_notebook", "nlm_add_source",
            "nlm_generate_podcast",
        ],
        "includes": [],
        "description": "Google NotebookLM 연동",
    },

    # ════════════════════════════════
    # 역할별 합성 Toolset (includes 사용)
    # ════════════════════════════════

    # Writer 역할: 수집 + AI 생성 + RAG
    "role_writer": {
        "tools": [],
        "includes": ["collector", "core", "rag", "content", "agent_control"],
        "description": "콘텐츠 작성 역할 (수집→생성)",
    },

    # Editor 역할: 분석 + 품질 검증
    "role_editor": {
        "tools": [],
        "includes": ["analysis", "quality", "agent_control"],
        "description": "콘텐츠 편집/검증 역할",
    },

    # SEO 역할: SEO + 분석
    "role_seo": {
        "tools": [],
        "includes": ["seo", "analysis", "agent_control"],
        "description": "SEO 최적화 역할",
    },

    # Publisher 역할: 내보내기 + 연동 + MCP
    "role_publisher": {
        "tools": [],
        "includes": ["export", "integrations", "mcp", "schedule", "agent_control"],
        "description": "콘텐츠 발행 역할",
    },

    # Media 역할: 미디어 생성
    "role_media": {
        "tools": [],
        "includes": ["media", "agent_control"],
        "description": "미디어 에셋 생성 역할",
    },

    # Full: 일반 자동화 도구. 발행/예약처럼 외부 상태를 바꾸는 도구는
    # 명시적인 role_publisher 선택 없이는 노출하지 않는다.
    "full": {
        "tools": [],
        "includes": [
            "collector", "analysis", "seo", "content", "core",
            "quality", "media", "transcript", "platform", "rag",
            "export", "integrations",
            "agent_control", "analytics",
            "notebooklm",
        ],
        "description": "일반 자동화 도구 (발행·예약 제외)",
    },
}


def resolve_toolset(
    name: str,
    _visited: Optional[Set[str]] = None,
) -> List[str]:
    """Toolset 이름을 재귀적으로 해석하여 도구 이름 목록을 반환합니다.

    includes를 따라가며 중복 없이 모든 도구를 수집합니다.
    순환 참조를 방지합니다.

    Args:
        name: Toolset 이름
        _visited: 순환 참조 방지용 (내부)

    Returns:
        도구 이름 목록 (중복 없음)
    """
    if _visited is None:
        _visited = set()

    if name in _visited:
        return []  # 순환 참조 방지
    _visited.add(name)

    toolset = TOOLSETS.get(name)
    if not toolset:
        return []

    tools: list = list(toolset.get("tools", []))

    for included in toolset.get("includes", []):
        tools.extend(resolve_toolset(included, _visited))

    # 중복 제거 (순서 유지)
    seen: set = set()
    unique = []
    for t in tools:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


def resolve_toolsets(names: Sequence[str]) -> List[str]:
    """여러 Toolset을 한 번에 해석합니다."""
    all_tools: list = []
    visited: Set[str] = set()
    for name in names:
        all_tools.extend(resolve_toolset(name, visited))

    seen: set = set()
    unique = []
    for t in all_tools:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


def resolve_toolset_names(names: Sequence[str]) -> List[str]:
    """Toolset 이름 목록을 leaf toolset 이름으로 해석합니다.

    합성 Toolset(includes)을 재귀적으로 펼쳐서
    실제 도메인 toolset 이름 목록을 반환합니다.

    예: ["role_writer"] → ["collector", "core", "rag", "content", "agent_control"]
    """
    result: List[str] = []
    visited: Set[str] = set()

    def _resolve(name: str) -> None:
        if name in visited:
            return
        visited.add(name)
        ts = TOOLSETS.get(name)
        if not ts:
            return
        includes = ts.get("includes", [])
        if includes:
            for inc in includes:
                _resolve(inc)
        # leaf toolset이거나 자체 tools가 있으면 포함
        if not includes or ts.get("tools"):
            result.append(name)

    for name in names:
        _resolve(name)

    # 중복 제거 (순서 유지)
    seen: set = set()
    unique = []
    for n in result:
        if n not in seen:
            seen.add(n)
            unique.append(n)
    return unique


def get_toolset_description(name: str) -> str:
    """Toolset 설명 반환."""
    ts = TOOLSETS.get(name)
    return ts.get("description", "") if ts else ""


def list_toolset_names() -> List[str]:
    """모든 Toolset 이름 반환."""
    return list(TOOLSETS.keys())
