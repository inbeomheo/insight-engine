"""Paddle 결제 라우트 (F4-16) — payment_routes.py에서 분리."""
from flask import jsonify, request

from routes.blog_routes import blog_bp
from routes.payment._shared import payment_exception_response
from services.data.supabase_service import require_auth
from utils.responses import error_response


@blog_bp.route('/api/paddle/status', methods=['GET'])
@require_auth
def paddle_status():
    """Paddle 설정 상태 조회"""
    from services.payment.paddle_service import paddle_service
    return jsonify({'configured': paddle_service.is_configured})


@blog_bp.route('/api/paddle/webhook', methods=['POST'])
def paddle_webhook():
    """Paddle 웹훅 수신 (서명 검증 포함)"""
    from services.payment.paddle_service import paddle_service

    payload = request.get_data()
    signature = request.headers.get('Paddle-Signature', '')

    if not paddle_service.verify_webhook(payload, signature):
        return error_response('[인증 실패] Paddle 웹훅 서명 검증에 실패했습니다.', 400)

    data = request.get_json(silent=True) or {}
    event_type = data.get('event_type', '')
    event_data = data.get('data', {})

    try:
        result = paddle_service.handle_webhook(event_type, event_data)
        return jsonify(result)
    except Exception as e:
        return payment_exception_response(
            'Paddle 웹훅 처리 오류',
            e,
            '[결제 오류] Paddle 웹훅 처리에 실패했습니다.'
        )


@blog_bp.route('/api/paddle/subscription/<subscription_id>', methods=['GET'])
@require_auth
def paddle_get_subscription(subscription_id):
    """Paddle 구독 정보 조회"""
    from services.payment.paddle_service import paddle_service

    sub = paddle_service.get_subscription(subscription_id)
    if not sub:
        return error_response('구독 정보를 찾을 수 없습니다.', 404)
    return jsonify(sub)
