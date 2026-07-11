"""DDD 리팩토링 베이스라인 자동 측정 스크립트.

사용법
------
    python -m tests.architecture.baseline > tests/architecture/baseline.json

목적
----
마스터 플랜 성공 지표(current_app 침투 0, supabase_service 직결 import 0 등)를
주기적으로 추적하기 위한 측정 도구. 테스트 실행 시 자동으로 호출되지 않으며,
의도적으로 실행해서 결과를 baseline.json으로 스냅샷한다.

출력 스키마
-----------
{
    "measured_at": "ISO-8601 timestamp",
    "current_app_usage": [
        {"file": "services/core/ai_service.py", "lines": [15, 136, ...]},
        ...
    ],
    "supabase_direct_imports": [
        {"file": "services/usage/usage_service.py", "lines": [5]},
        ...
    ],
    "cross_subdomain_imports": [
        {"source": "analytics", "target": "core", "count": 17},
        ...
    ],
    "service_file_line_counts": {
        "services/core/content_service.py": 809,
        ...
    },
    "summary": {
        "current_app_files": N,
        "supabase_direct_import_files": N,
        "cross_subdomain_pairs": N
    }
}
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = PROJECT_ROOT / "services"
ROUTES_DIR = PROJECT_ROOT / "routes"

# 정밀 추적할 God Layer 파일들 (test_domain_boundaries.py의 LINE_LIMITS와 동일 키 사용)
TRACKED_LINE_FILES = [
    "services/core/content_service.py",
    "services/core/ai_service.py",
    "services/data/supabase_service.py",
    "services/data/workspace_service.py",
    # 다음 라운드에서 슬림화 대상이 될 수 있는 후보 (참고용)
    "services/core/fusion_service.py",
]


def _iter_python_files(base: Path):
    for path in base.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _rel(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def measure_current_app_usage() -> List[Dict]:
    """services/ 하위에서 current_app 참조 위치(파일+라인 번호)를 수집."""
    pattern = re.compile(r"\bcurrent_app\b")
    results: List[Dict] = []
    for path in _iter_python_files(SERVICES_DIR):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        hits = [i + 1 for i, line in enumerate(lines) if pattern.search(line)]
        if hits:
            results.append({"file": _rel(path), "lines": hits})
    results.sort(key=lambda r: r["file"])
    return results


def measure_supabase_direct_imports() -> List[Dict]:
    """services/data/* 를 제외하고 supabase_service를 직접 import하는 위치."""
    pattern = re.compile(
        r"(?:from\s+services\.data\.supabase_service\b|import\s+services\.data\.supabase_service\b)"
    )
    results: List[Dict] = []
    for base in (SERVICES_DIR, ROUTES_DIR):
        if not base.exists():
            continue
        for path in _iter_python_files(base):
            rel = _rel(path)
            if rel.startswith("services/data/"):
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            hits = [i + 1 for i, line in enumerate(lines) if pattern.search(line)]
            if hits:
                results.append({"file": rel, "lines": hits})
    results.sort(key=lambda r: r["file"])
    return results


def measure_cross_subdomain_imports() -> List[Dict]:
    """services/X에서 services/Y(X≠Y)를 import하는 패턴의 카운트.

    BC(Bounded Context) 경계 위반 가능성이 있는 호출 경로 추적용.
    """
    pattern = re.compile(
        r"(?:from\s+services\.(\w+)(?:\.[\w]+)*\s+import|import\s+services\.(\w+))"
    )
    counts: Dict[str, int] = {}
    for path in _iter_python_files(SERVICES_DIR):
        rel = _rel(path)
        # services/X/.../foo.py → X 추출
        parts = rel.split("/")
        if len(parts) < 3:
            continue
        src_subdomain = parts[1]
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in pattern.finditer(text):
            target = match.group(1) or match.group(2)
            if not target or target == src_subdomain or target.startswith("_"):
                continue
            key = f"{src_subdomain} -> {target}"
            counts[key] = counts.get(key, 0) + 1

    results = []
    for key, count in counts.items():
        src, tgt = key.split(" -> ")
        results.append({"source": src, "target": tgt, "count": count})
    results.sort(key=lambda r: (-r["count"], r["source"], r["target"]))
    return results


def measure_service_file_line_counts() -> Dict[str, int]:
    """추적 대상 파일들의 현재 라인 수."""
    out: Dict[str, int] = {}
    for rel in TRACKED_LINE_FILES:
        path = PROJECT_ROOT / rel
        if not path.exists():
            out[rel] = -1  # 파일 없음 표시
            continue
        out[rel] = sum(1 for _ in path.open("r", encoding="utf-8"))
    return out


def build_report() -> Dict:
    current_app = measure_current_app_usage()
    supabase = measure_supabase_direct_imports()
    cross = measure_cross_subdomain_imports()
    lines = measure_service_file_line_counts()
    return {
        "measured_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "current_app_usage": current_app,
        "supabase_direct_imports": supabase,
        "cross_subdomain_imports": cross,
        "service_file_line_counts": lines,
        "summary": {
            "current_app_files": len(current_app),
            "current_app_occurrences": sum(len(item["lines"]) for item in current_app),
            "supabase_direct_import_files": len(supabase),
            "supabase_direct_import_occurrences": sum(len(item["lines"]) for item in supabase),
            "cross_subdomain_pairs": len(cross),
        },
    }


def main() -> int:
    report = build_report()
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
