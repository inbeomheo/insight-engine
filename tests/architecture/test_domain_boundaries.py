"""DDD 리팩토링 안전망: 도메인 경계 회귀 방지 테스트.

목적
----
Phase 0~10 리팩토링이 진행되는 동안, 이미 측정된 베이스라인보다 더 나빠지지
않도록 가드하는 아키텍처 테스트 모음.

- A: `flask.current_app` 침투(파일 단위) 베이스라인 — Phase 5/10에 0이 목표.
- B: `services.data.supabase_service` 직결 import 베이스라인 — Phase 2(ACL) 후 0이 목표.
- C: BC(Bounded Context) 간 크로스 import 가드 — Phase 3+에서 활성화. 현재는 skip.
- D: 주요 God Layer 파일의 라인 수 회귀 방지 — Phase 5/8 종료 시 LIMIT을 점진적으로 낮춤.

베이스라인 수치는 `tests.architecture.baseline` 스크립트로 재측정 가능.
새로운 침투가 발생하면 테스트가 실패하므로, 의도된 변경이라면 베이스라인을 먼저 갱신한다.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, Set

import pytest


# 프로젝트 루트 (tests/architecture/test_domain_boundaries.py → 2단계 위)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = PROJECT_ROOT / "services"
ROUTES_DIR = PROJECT_ROOT / "routes"


def _iter_python_files(base: Path) -> Iterable[Path]:
    """주어진 경로 하위의 모든 .py 파일을 순회 (캐시 디렉토리 제외)."""
    for path in base.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _rel(path: Path) -> str:
    """프로젝트 루트 기준 상대 경로 (POSIX 형식)."""
    return path.relative_to(PROJECT_ROOT).as_posix()


# ---------------------------------------------------------------------------
# A. flask.current_app 침투 베이스라인
# ---------------------------------------------------------------------------

# 2026-05-21 측정 기준: services/ 내 current_app을 사용하는 파일 5개.
# 이 베이스라인을 줄이는 작업은 Phase 5(ContentGeneration ACL) / Phase 7(Publishing) 등에서 수행.
# TODO(Phase 5+): logging_config는 fallback 경로라 가장 마지막에 제거. 우선순위:
#   1. content_service.py / ai_service.py (Phase 5 - ContentGeneration BC)
#   2. quality_service.py (Phase 5 - ContentEvaluation BC)
#   3. transcript/_shared.py (Phase 5 - Transcript BC)
#   4. logging_config.py (마지막, fallback 경로)
CURRENT_APP_BASELINE: Set[str] = {
    "services/core/ai_service.py",
    "services/core/content_service.py",
    "services/core/logging_config.py",
    "services/quality/quality_service.py",
    "services/transcript/_shared.py",
}


def _files_using_current_app() -> Set[str]:
    """services/ 하위에서 current_app을 참조하는 파일 집합."""
    pattern = re.compile(r"\bcurrent_app\b")
    offenders: Set[str] = set()
    for path in _iter_python_files(SERVICES_DIR):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if pattern.search(text):
            offenders.add(_rel(path))
    return offenders


def test_flask_current_app_not_in_domain_modules():
    """services/ 도메인 로직에 `from flask import current_app`가 침투한 위치를 베이스라인 대비 측정.

    DDD 리팩토링 진행 중 새로운 침투를 막기 위한 가드.
    Phase 5/10까지 0으로 줄여야 함 (마스터 플랜 성공 지표).
    """
    actual = _files_using_current_app()
    new_offenders = actual - CURRENT_APP_BASELINE
    assert not new_offenders, (
        "새로운 current_app 침투가 감지되었습니다. "
        "도메인 서비스에서 Flask 컨텍스트를 직접 참조하지 마세요.\n"
        f"신규 침투 파일: {sorted(new_offenders)}\n"
        "해결: 로거/설정을 인자로 주입받거나 services/core/logging_config의 헬퍼를 사용하세요."
    )

    # 베이스라인이 줄어들었다면 (개선됨) — 알림용 메시지로 commit 유도
    fixed = CURRENT_APP_BASELINE - actual
    if fixed:
        # 실패시키지는 않지만, 베이스라인 갱신이 필요함을 표시
        pytest.skip(
            f"베이스라인 갱신 필요: 다음 파일에서 current_app이 제거됨 → {sorted(fixed)}. "
            "CURRENT_APP_BASELINE에서도 제거하세요."
        )


# ---------------------------------------------------------------------------
# B. services.data.supabase_service 직결 import 베이스라인
# ---------------------------------------------------------------------------

# 2026-05-21 최초 측정: 비-data 도메인에서 supabase_service 직결 import 44 파일.
# 2026-05-21 Issue #17 소PR A: 인프라 헬퍼(`get_supabase`, `is_supabase_enabled`,
#   `_get_admin_client`, `encrypt_api_key`, `decrypt_api_key`)를
#   `src/shared/infrastructure/supabase_client.py`로 이전. 순수 인프라만 쓰던
#   6 파일이 베이스라인에서 제거됨. → 38 파일
# 2026-05-21 Issue #17 소PR B-1: `require_auth` 등 인증 데코레이터를
#   `src/contexts/identity/interface/auth_decorators.py`로 이전 + 33 단일 import
#   라우트 갱신 + payment_routes.py / auth_routes.py / blog_routes.py 다중 import
#   재구성. routes 32 파일이 베이스라인에서 제거됨. → 6 파일.
# 2026-05-22 Issue #19 Phase 5-a: Content/Library BC 골격 + `save_history_entry`
#   편의 함수 도입. routes/generation_helpers.py가 새 BC를 경유하도록 마이그레이션.
#   추가로 routes/advanced_routes.py + routes/utility/external.py의 lazy
#   `is_supabase_enabled` import를 `src.shared.infrastructure.supabase_client`로
#   직접 치환. utility/external.py의 legacy history 조회 호출은
#   클래스 자체가 존재하지 않는 dead code였음 (try/except로 silent fail) — 명시적
#   빈 리스트로 단순화. → 3 파일.
# 2026-05-22 Issue #19 Phase 5-b: routes/blog_routes.py의 history import를
#   Content/Library BC로, 인프라 import를 src.shared.infrastructure로 분리.
#   라인 616의 lazy `get_supabase` import도 상단 인프라 import로 통합. → 2 파일.
# 2026-05-22 Issue #19 Phase 5-c: Channel Monitoring BC 도입 +
#   `routes/auth/channel_monitoring.py` .table() 3건 + `blog_routes.py:636`
#   배치 INSERT BC 위임. supabase_service import 변화 없음 (.table() 7→3).
# 2026-05-22 Issue #19 Phase 5-d: Content/Library `fetch_admin_history_stats`
#   + Identity `fetch_daily_usage_history` 편의 함수 추가. admin_dashboard 2건 +
#   payment_routes 1건 .table() 정리. payment_routes:288의 잘못된
#   `__import__('services.supabase_service', ...)` dead code도 함께 정정. .table() 3→0.
# 2026-05-22 Issue #19 Phase 5-e: services/data/ 아래 도메인별 facade 6종 신설
#   (api_key_storage/custom_style/snippet/usage_admin/content_admin/account_admin).
#   routes/auth_routes.py 13 함수 다중 import를 facade로 분리. services/usage/
#   usage_service.py를 src.shared + identity.domain.constants + usage_admin_facade
#   조합으로 재구성. → **0 파일** 달성.
#
# 베이스라인 완전 해소 (44 → 0). Issue #19 완료.
SUPABASE_DIRECT_IMPORT_BASELINE: Set[str] = set()


def _files_importing_supabase_service_directly() -> Set[str]:
    """services/data/* 를 제외하고, supabase_service를 직접 import하는 파일 집합."""
    pattern = re.compile(
        r"(?:from\s+services\.data\.supabase_service\b|import\s+services\.data\.supabase_service\b)"
    )
    offenders: Set[str] = set()
    for base in (SERVICES_DIR, ROUTES_DIR):
        if not base.exists():
            continue
        for path in _iter_python_files(base):
            rel = _rel(path)
            # data 도메인 내부는 정상 (Identity&Access ACL 정리 후 contexts/identity로 이전 예정)
            if rel.startswith("services/data/"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if pattern.search(text):
                offenders.add(rel)
    return offenders


def test_supabase_service_direct_imports_baseline():
    """services/data/supabase_service를 직접 import하는 비-data 도메인 파일 베이스라인.

    분석 에이전트가 식별한 지점들을 베이스라인으로 박아두고, 신규 침투를 차단한다.
    Phase 2 (Identity&Access ACL) 완료 시 0으로 줄어야 함.
    """
    actual = _files_importing_supabase_service_directly()
    new_offenders = actual - SUPABASE_DIRECT_IMPORT_BASELINE
    assert not new_offenders, (
        "supabase_service를 새로운 위치에서 직접 import하고 있습니다. "
        "Identity&Access ACL 또는 적절한 BC 인터페이스를 경유하세요.\n"
        f"신규 침투 파일: {sorted(new_offenders)}"
    )

    fixed = SUPABASE_DIRECT_IMPORT_BASELINE - actual
    if fixed:
        pytest.skip(
            f"베이스라인 갱신 필요: 다음 파일에서 supabase_service 직결 import가 제거됨 → "
            f"{sorted(fixed)}. SUPABASE_DIRECT_IMPORT_BASELINE에서도 제거하세요."
        )


# ---------------------------------------------------------------------------
# C. BC(Bounded Context) 간 cross-import 가드 — Phase 3+에서 활성화
# ---------------------------------------------------------------------------

# TODO(Phase 3+): 아래 테스트를 활성화하려면 src/contexts/{identity,content_generation,...}
# 디렉토리 구조가 먼저 마련되어야 함. 각 BC는 application/ports.py로만 외부에 노출되며,
# 다른 BC가 직접 infrastructure/도메인 객체를 import 하면 위반.
@pytest.mark.skip(reason="Phase 3+ 도입 — src/contexts/ 디렉토리 생성 후 활성화")
def test_no_cross_context_imports():
    """BC 간 import는 application/ports.py 인터페이스를 통해서만 허용.

    예) contexts.publishing 모듈은 contexts.content_generation의 도메인/인프라를
    직접 import 할 수 없고, 오직 contexts.content_generation.application.ports.* 만
    import 가능.

    구현 가이드:
    - src/contexts 하위 BC 디렉토리를 순회
    - 각 모듈의 import 문 AST 파싱
    - 다른 BC 패키지를 참조한다면 .application.ports.* 가 아닌 경우 실패
    """
    # TODO: src/contexts/ 구조 확정 후 구현
    pytest.fail("Phase 3+ 가드 미구현")


# ---------------------------------------------------------------------------
# D. 주요 God Layer 파일의 라인 수 회귀 방지
# ---------------------------------------------------------------------------

# 2026-05-21 측정 기준 현재 라인 수 (limit은 약간의 버퍼 포함).
# Phase 5(ContentGeneration), Phase 2(Identity&Access), Phase 8(Workspace) 진행 시
# limit을 점진적으로 낮춰가야 함.
#
# TODO(Phase 5/8):
#   - content_service.py 분리: 자막추출 / 댓글수집 / 폴백체인 → Transcript BC 이관
#   - ai_service.py 분리: 프롬프트 조합 / 모델 호출 / RAG 주입 → 별도 클래스
#   - supabase_service.py 분리: 인증 / CRUD / 어드민 쿼리 → ACL 패턴 적용
#   - workspace_service.py 분리: CRUD / 초대 / 권한 / 승인 플로우
LINE_LIMITS = {
    "services/core/content_service.py": 900,   # 현재 809
    "services/core/ai_service.py": 700,        # 현재 613
    "services/data/supabase_service.py": 800,  # 현재 721
    "services/data/workspace_service.py": 600, # 현재 532
}


def test_largest_service_files_line_count():
    """주요 God Layer 파일이 더 커지지 않도록 가드.

    리팩토링이 진행될수록 LINE_LIMITS의 상한을 낮춰 점진적 슬림화를 유도.
    """
    violations = []
    for rel_path, limit in LINE_LIMITS.items():
        path = PROJECT_ROOT / rel_path
        if not path.exists():
            # 파일이 사라졌다면 (예: 분리됨) — LIMITS 갱신 필요
            violations.append(f"{rel_path}: 파일이 존재하지 않음 (LINE_LIMITS에서 제거 필요)")
            continue
        line_count = sum(1 for _ in path.open("r", encoding="utf-8"))
        if line_count > limit:
            violations.append(
                f"{rel_path}: {line_count}줄 (한도 {limit}). "
                "신규 코드 추가 대신 분리/위임을 고려하세요."
            )
    assert not violations, "\n".join(violations)
