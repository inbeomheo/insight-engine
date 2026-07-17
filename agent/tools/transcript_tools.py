"""Transcript 서비스 도구 자동 등록."""
import logging

from agent.tools._auto_register import register_service_tools


register_service_tools(
    "services.transcript",
    "transcript",
    skip_modules={"whisper_service"},
    logger=logging.getLogger(__name__),
)
