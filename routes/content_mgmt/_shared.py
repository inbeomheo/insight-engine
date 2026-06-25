"""content_mgmt 서브 라우트 공용 응답 헬퍼."""
from flask import jsonify, request

from utils.responses import safe_error_or_fallback


def _json(data, status=200):
    return jsonify(data), status


def _err(msg, status=400):
    return jsonify({'error': msg}), status


def _get_json():
    return request.get_json(silent=True) or {}


def _safe_route_error(message, fallback_message):
    return safe_error_or_fallback(message, fallback_message)
