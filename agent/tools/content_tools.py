"""Content 서비스 도구 자동 등록."""
import logging

from agent.tools._auto_register import register_service_tools


register_service_tools(
    "services.content",
    "content",
    skip_modules={"multi_source_collector"},
    default_content_description="입력 텍스트",
    logger=logging.getLogger(__name__),
)
