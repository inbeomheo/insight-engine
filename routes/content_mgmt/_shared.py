"""content_mgmt 서브 라우트 공용 응답 헬퍼."""
from flask import jsonify, request

from utils.responses import sanitize_error_for_client


def _json(data, status=200):
    return jsonify(data), status


def _err(msg, status=400):
    return jsonify({'error': msg}), status


def _get_json():
    return request.get_json(silent=True) or {}


def _safe_route_error(message, fallback_message):
    safe_message = sanitize_error_for_client(str(message or ''))
    if safe_message.startswith('[서버 오류]'):
        return fallback_message
    return safe_message
