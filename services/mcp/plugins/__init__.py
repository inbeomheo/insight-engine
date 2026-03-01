"""
플러그인 자동 등록

이 모듈이 import되면 기본 플러그인들이 레지스트리에 자동 등록됩니다.
"""
from ..registry import plugin_registry
from .naver_blog import NaverBlogPlugin
from .wordpress import WordPressPlugin

plugin_registry.register('naver_blog', NaverBlogPlugin())
plugin_registry.register('wordpress', WordPressPlugin())
