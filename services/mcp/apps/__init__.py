"""
MCP 앱 자동 등록

이 모듈이 import되면 기본 앱들이 레지스트리에 자동 등록됩니다.
"""
from ..mcp_apps import app_registry
from .content_preview import ContentPreviewApp
from .inline_editor import InlineEditorApp

app_registry.register(ContentPreviewApp())
app_registry.register(InlineEditorApp())
