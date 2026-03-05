"""
요청 검증 미들웨어 (F9-18)
JSON 스키마 기반 요청 바디 검증, 공통 필드 sanitize
"""
import json
import logging
import re
from functools import wraps
from typing import Any, Dict, List, Optional

from flask import request, jsonify

logger = logging.getLogger(__name__)

# URL 패턴 (YouTube + 일반 웹)
_URL_PATTERN = re.compile(
    r'^https?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
    r'localhost|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$',
    re.IGNORECASE
)

# 허용 스타일 목록 (config와 동기화 필요)
VALID_STYLES = {
    'blog_seo', 'summary', 'tutorial', 'qna', 'app_ideas',
    'yozm_it', 'brunch_essay', 'naver_popular', 'sns_post',
    'newsletter', 'show_notes', 'shorts_script', 'geo_seo', 'course',
    'comment_summary', 'cited_summary', 'chapter_split', 'mindmap',
}

VALID_LENGTHS = {'short', 'medium', 'long'}
VALID_WRITING_STYLES = {'conversational', 'explanatory', 'casual', 'expert'}
VALID_LANGUAGES = {'ko', 'en', 'ja'}


def validate_url(url: str) -> bool:
    """URL 형식 검증"""
    return bool(_URL_PATTERN.match(url))


def sanitize_string(value: str, max_length: int = 2000) -> str:
    """문자열 sanitize: 앞뒤 공백 제거, 길이 제한"""
    if not isinstance(value, str):
        return ''
    return value.strip()[:max_length]


def validate_generate_request(data: Dict[str, Any]) -> List[str]:
    """
    /generate 요청 데이터 검증

    Returns:
        에러 메시지 리스트 (빈 리스트면 유효)
    """
    errors = []

    # URL 검증
    urls = data.get('urls', [])
    if not urls:
        url = data.get('url', '')
        if not url:
            errors.append("URL이 필요합니다 (url 또는 urls 필드)")
        elif not validate_url(url):
            errors.append(f"유효하지 않은 URL 형식: {url[:100]}")
    else:
        if not isinstance(urls, list) or len(urls) > 10:
            errors.append("urls는 최대 10개의 배열이어야 합니다")
        else:
            for u in urls:
                if not validate_url(u):
                    errors.append(f"유효하지 않은 URL: {u[:100]}")

    # 스타일 검증
    style = data.get('style_id', 'blog_seo')
    if style and style not in VALID_STYLES:
        errors.append(f"지원하지 않는 스타일: {style}")

    # 모디파이어 검증
    length = data.get('length', 'medium')
    if length and length not in VALID_LENGTHS:
        errors.append(f"유효하지 않은 길이 옵션: {length} (short/medium/long)")

    writing_style = data.get('writing_style', 'conversational')
    if writing_style and writing_style not in VALID_WRITING_STYLES:
        errors.append(f"유효하지 않은 문체: {writing_style}")

    language = data.get('language', 'ko')
    if language and language not in VALID_LANGUAGES:
        errors.append(f"지원하지 않는 언어: {language} (ko/en/ja)")

    return errors


def require_json(f):
    """JSON Content-Type 검증 데코레이터"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return jsonify({'error': 'Content-Type: application/json 이 필요합니다'}), 415
        return f(*args, **kwargs)
    return wrapper


def validate_request_size(max_bytes: int = 1 * 1024 * 1024):
    """요청 바디 크기 제한 데코레이터 팩토리 (기본 1MB)"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            content_length = request.content_length
            if content_length and content_length > max_bytes:
                return jsonify({
                    'error': f'요청 크기 초과 (최대 {max_bytes // 1024}KB)'
                }), 413
            return f(*args, **kwargs)
        return wrapper
    return decorator


def validate_generate(f):
    """콘텐츠 생성 요청 통합 검증 데코레이터"""
    @wraps(f)
    @require_json
    def wrapper(*args, **kwargs):
        data = request.get_json(silent=True) or {}
        errors = validate_generate_request(data)
        if errors:
            logger.warning("요청 검증 실패: %s", errors)
            return jsonify({'error': '; '.join(errors)}), 400
        return f(*args, **kwargs)
    return wrapper


class RequestValidatorMiddleware:
    """
    Flask 앱 레벨 요청 검증 미들웨어

    사용법:
        from middleware.request_validator import RequestValidatorMiddleware
        RequestValidatorMiddleware(app)
    """

    # 크기 제한 적용 엔드포인트 (bytes)
    SIZE_LIMITS = {
        '/generate': 2 * 1024 * 1024,          # 2MB
        '/api/knowledge/upload': 50 * 1024 * 1024,  # 50MB (파일 업로드)
    }

    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def init_app(self, app):
        app.before_request(self._check_request_size)
        logger.info("RequestValidatorMiddleware 초기화 완료")

    def _check_request_size(self):
        path = request.path
        limit = self.SIZE_LIMITS.get(path)
        if limit is None:
            # 기본 글로벌 제한: 10MB
            limit = 10 * 1024 * 1024

        content_length = request.content_length
        if content_length and content_length > limit:
            return jsonify({
                'error': f'요청 크기 초과 (경로: {path}, 최대: {limit // 1024}KB)'
            }), 413
