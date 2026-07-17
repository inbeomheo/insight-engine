"""Analysis 서비스 도구 자동 등록."""
import logging

from agent.tools._auto_register import register_service_tools


def _register_analysis_tools() -> int:
    return register_service_tools(
        "services.analysis",
        "analysis",
        fallback_description_suffix=" 분석",
        default_content_description="분석할 텍스트 콘텐츠",
        logger=logging.getLogger(__name__),
    )


_register_analysis_tools()
