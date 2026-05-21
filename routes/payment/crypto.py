"""암호화폐 결제 라우트 (F4-17) — payment_routes.py에서 분리."""
from flask import g, jsonify, request

from routes.blog_routes import blog_bp
from routes.payment._shared import payment_exception_response, safe_payment_error_response
from services.data.supabase_service import require_auth
from utils.responses import error_response


@blog_bp.route('/api/crypto/charge', methods=['POST'])
@require_auth
def crypto_create_charge():
    """암호화폐 결제 요청 생성"""
    from services.payment.crypto_service import crypto_service

    if not crypto_service.is_configured:
        return error_response('Coinbase Commerce가 설정되지 않았습니다.', 503)

    data = request.get_json(silent=True) or {}
    amount = data.get('amount')
    if not amount or float(amount) <= 0:
        return error_response('유효한 amount가 필요합니다.')

    try:
        result = crypto_service.create_charge(
            user_id=g.user_id,
            amount=float(amount),
            currency=data.get('currency', 'USD'),
            description=data.get('description', ''),
        )
        if 'error' in result:
            return safe_payment_error_response(
                result['error'],
                '[결제 오류] 암호화폐 결제 요청 생성에 실패했습니다.',
                500
            )
        return jsonify(result), 201
    except Exception as e:
        return payment_exception_response(
            '암호화폐 결제 요청 생성 오류',
            e,
            '[결제 오류] 암호화폐 결제 요청 생성에 실패했습니다.'
        )


@blog_bp.route('/api/crypto/charge/<charge_id>', methods=['GET'])
@require_auth
def crypto_get_charge(charge_id):
    """암호화폐 결제 요청 단건 조회"""
    from services.payment.crypto_service import crypto_service

    charge = crypto_service.get_charge(charge_id)
    if not charge:
        return error_response('결제 요청을 찾을 수 없습니다.', 404)
    return jsonify(charge)


@blog_bp.route('/api/crypto/webhook', methods=['POST'])
def crypto_webhook():
    """Coinbase Commerce 웹훅 수신"""
    from services.payment.crypto_service import crypto_service

    payload = request.get_data()
    signature = request.headers.get('X-CC-Webhook-Signature', '')

    if not crypto_service.verify_webhook(payload, signature):
        return error_response('웹훅 서명 검증 실패', 401)

    data = request.get_json(silent=True) or {}
    event_type = data.get('type', '')
    event_data = data.get('data', {})

    try:
        result = crypto_service.handle_webhook(event_type, event_data)
        return jsonify(result)
    except Exception as e:
        return payment_exception_response(
            '암호화폐 웹훅 처리 오류',
            e,
            '[결제 오류] 웹훅 처리 중 문제가 발생했습니다.'
        )
