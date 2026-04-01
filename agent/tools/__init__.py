"""
Tool 래핑 모듈 — 기존 서비스를 Agent Tool로 등록

각 파일이 import 시 자동으로 registry.register()를 호출합니다.
Phase 2에서 서비스 도메인별로 구현됩니다.

패턴:
    # agent/tools/analysis_tools.py
    from agent.registry import registry
    from services.analysis.readability_service import analyze_readability

    registry.register(
        name="analyze_readability",
        toolset="analysis",
        description="텍스트 가독성 분석 (Flesch-Kincaid 기반)",
        parameters={"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]},
        handler=lambda args, **kw: analyze_readability(args["content"]),
    )
"""

# Phase 2에서 자동 디스커버리 구현
# discover_tools()가 이 디렉토리의 모든 *_tools.py를 import
import importlib
import logging
import os
import pkgutil

logger = logging.getLogger(__name__)


def discover_tools() -> int:
    """tools/ 디렉토리의 모든 도구 모듈을 자동 import합니다.

    Returns:
        import된 모듈 수
    """
    package_dir = os.path.dirname(__file__)
    count = 0

    for _, module_name, _ in pkgutil.iter_modules([package_dir]):
        if module_name.startswith("_"):
            continue
        try:
            importlib.import_module(f"agent.tools.{module_name}")
            count += 1
            logger.debug("도구 모듈 로드: %s", module_name)
        except Exception as e:
            logger.warning("도구 모듈 로드 실패: %s — %s", module_name, e)

    from agent.registry import registry
    logger.info(
        "도구 디스커버리 완료: %d 모듈, %d 도구 등록",
        count, registry.tool_count,
    )
    return count
