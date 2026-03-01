"""
MCP 플러그인 시스템

외부 서비스 발행을 위한 플러그인 레지스트리 패턴.
"""
from .registry import PluginRegistry, plugin_registry

# 플러그인 자동 등록 트리거
from . import plugins  # noqa: F401

__all__ = ['PluginRegistry', 'plugin_registry']
