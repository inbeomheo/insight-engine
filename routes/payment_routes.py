"""
결제 관련 라우트
크레딧, Stripe 결제, 구독, 체험, 사용량, 레퍼럴, API 키
"""
import logging

from flask import request, jsonify, g

from routes.blog_routes import blog_bp
from utils.responses import success_response, error_response, sanitize_error_for_client
from services.data.supabase_service import require_auth, is_supabase_enabled

logger = logging.getLogger(__name__)


def _safe_payment_error_response(message, fallback_message, status_code=500):
    safe_message = sanitize_error_for_client(str(message or ''))
    if safe_message.startswith('[서버 오류]'):
        safe_message = fallback_message
    return error_response(safe_message, status_code)


def _payment_exception_response(log_context, error, fallback_message, status_code=500):
    logger.error('%s: %s', log_context, error, exc_info=True)
    return error_response(fallback_message, status_code)


# =============================================
# 크레딧 API (F4-01)
# =============================================

@blog_bp.route('/api/credits/balance', methods=['GET'])
@require_auth
def get_credit_balance():
    """크레딧 잔액 조회"""
    from services.usage.credit_service import credit_service
    balance = credit_service.get_balance(g.user_id)
    return jsonify(balance)


@blog_bp.route('/api/credits/purchase', methods=['POST'])
@require_auth
def purchase_credits():
    """크레딧 직접 구매 (Stripe Checkout으로 리다이렉트)"""
    from services.payment.stripe_service import stripe_service

    if not stripe_service.is_enabled():
        return error_response('결제 시스템이 설정되지 않았습니다.', 503)

    data = request.get_json(silent=True) or {}
    price_id = data.get('price_id', '')
    if not price_id:
        return error_response('price_id가 필요합니다.')

    try:
        result = stripe_service.create_checkout_session(
            user_id=g.user_id,
            price_id=price_id,
            mode='payment',
        )
    except Exception as e:
        logger.error('크레딧 구매 세션 생성 오류: %s', e, exc_info=True)
        return error_response('[결제 오류] 결제 세션 생성 중 문제가 발생했습니다.', 500)

    if 'error' in result:
        return _safe_payment_error_response(
            result['error'],
            '[결제 오류] 크레딧 구매 세션 생성에 실패했습니다.',
            500
        )
    return jsonify(result)


@blog_bp.route('/api/credits/plans', methods=['GET'])
def get_credit_plans():
    """사용 가능한 플랜 목록"""
    from services.usage.credit_plan import get_all_plans
    return jsonify({'plans': get_all_plans()})


# =============================================
# Stripe 결제 API (F4-02)
# =============================================

@blog_bp.route('/api/payment/checkout', methods=['POST'])
@require_auth
def create_checkout():
    """Stripe Checkout 세션 생성"""
    from services.payment.stripe_service import stripe_service

    if not stripe_service.is_enabled():
        return error_response('결제 시스템이 설정되지 않았습니다.', 503)

    data = request.get_json(silent=True) or {}
    price_id = data.get('price_id', '')
    mode = data.get('mode', 'subscription')

    if not price_id:
        return error_response('price_id가 필요합니다.')

    try:
        result = stripe_service.create_checkout_session(
            user_id=g.user_id,
            price_id=price_id,
            mode=mode,
        )
    except Exception as e:
        logger.error('Stripe 체크아웃 세션 생성 오류: %s', e, exc_info=True)
        return error_response('[결제 오류] 체크아웃 세션 생성 중 문제가 발생했습니다.', 500)

    if 'error' in result:
        return _safe_payment_error_response(
            result['error'],
            '[결제 오류] 체크아웃 세션 생성에 실패했습니다.',
            500
        )
    return jsonify(result)


@blog_bp.route('/api/payment/webhook', methods=['POST'])
def stripe_webhook():
    """Stripe Webhook 수신 (서명 검증 포함)"""
    from services.payment.stripe_service import stripe_service

    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature', '')

    try:
        result = stripe_service.handle_webhook(payload, sig_header)
    except Exception as e:
        logger.error('Stripe 웹훅 처리 오류: %s', e, exc_info=True)
        return error_response('[결제 오류] 결제 웹훅 처리 중 문제가 발생했습니다.', 500)

    if not result.get('success'):
        error_message = str(result.get('error', '') or '')
        if '서명' in error_message or 'signature' in error_message.lower():
            return error_response('[인증 실패] 결제 웹훅 서명 검증에 실패했습니다.', 400)
        return _safe_payment_error_response(
            error_message,
            '[결제 오류] 결제 웹훅 처리에 실패했습니다.',
            400
        )
    return jsonify({'received': True})


# =============================================
# 구독 API (F4-03)
# =============================================

@blog_bp.route('/api/subscription', methods=['GET'])
@require_auth
def get_subscription():
    """현재 구독 정보 조회"""
    from services.payment.subscription_service import subscription_service
    try:
        sub = subscription_service.get_subscription(g.user_id)
        return jsonify(sub)
    except Exception as e:
        return _payment_exception_response(
            '구독 정보 조회 오류',
            e,
            '[서버 오류] 구독 정보를 조회할 수 없습니다.'
        )


@blog_bp.route('/api/subscription/upgrade', methods=['POST'])
@require_auth
def upgrade_subscription():
    """구독 업그레이드"""
    from services.payment.subscription_service import subscription_service

    data = request.get_json(silent=True) or {}
    new_plan = data.get('plan', 'pro')
    try:
        result = subscription_service.upgrade(g.user_id, new_plan)
        if not result.get('success'):
            return _safe_payment_error_response(
                result.get('error'),
                '[결제 오류] 구독 업그레이드에 실패했습니다.',
                500
            )
        return jsonify(result)
    except Exception as e:
        return _payment_exception_response(
            '구독 업그레이드 오류',
            e,
            '[결제 오류] 구독 업그레이드 처리 중 문제가 발생했습니다.'
        )


@blog_bp.route('/api/subscription/cancel', methods=['POST'])
@require_auth
def cancel_subscription():
    """구독 취소"""
    from services.payment.subscription_service import subscription_service
    try:
        result = subscription_service.cancel(g.user_id)
        if not result.get('success'):
            return _safe_payment_error_response(
                result.get('error'),
                '[결제 오류] 구독 취소에 실패했습니다.',
                500
            )
        return jsonify(result)
    except Exception as e:
        return _payment_exception_response(
            '구독 취소 오류',
            e,
            '[결제 오류] 구독 취소 처리 중 문제가 발생했습니다.'
        )


# =============================================
# 무료 체험 API (F4-04)
# =============================================

@blog_bp.route('/api/trial/start', methods=['POST'])
@require_auth
def start_trial():
    """7일 무료 체험 시작"""
    from services.payment.trial_service import trial_service
    try:
        result = trial_service.start_trial(g.user_id)
        if not result.get('success'):
            if result.get('already_used'):
                return error_response('이미 무료 체험을 사용하셨습니다.', 409)
            return _safe_payment_error_response(
                result.get('error'),
                '[서버 오류] 무료 체험 시작에 실패했습니다.',
                500
            )
        return jsonify(result)
    except Exception as e:
        return _payment_exception_response(
            '무료 체험 시작 오류',
            e,
            '[서버 오류] 무료 체험 시작에 실패했습니다.'
        )


@blog_bp.route('/api/trial/status', methods=['GET'])
@require_auth
def get_trial_status():
    """체험 상태 조회"""
    from services.payment.trial_service import trial_service
    try:
        trial = trial_service.get_trial(g.user_id)
        active = trial_service.is_trial_active(g.user_id)
        remaining = trial_service.get_remaining_days(g.user_id)
        return jsonify({
            'active': active,
            'remaining_days': remaining,
            'trial_end': trial.get('trial_end', ''),
        })
    except Exception as e:
        return _payment_exception_response(
            '체험 상태 조회 오류',
            e,
            '[서버 오류] 체험 상태를 조회할 수 없습니다.'
        )


# =============================================
# 사용량 대시보드 API (F4-05)
# =============================================

@blog_bp.route('/api/usage/my-usage', methods=['GET'])
@require_auth
def get_my_usage():
    """내 사용량 상세 조회 (크레딧 + 일일 사용량 + 히스토리)"""
    from services.usage.credit_service import credit_service
    from services.usage.usage_service import UsageService
    from services.payment.subscription_service import subscription_service

    try:
        balance = credit_service.get_balance(g.user_id)
        usage = UsageService.get_current(g.user_id)
        sub = subscription_service.get_subscription(g.user_id)

        # 최근 7일 사용 기록 (Supabase 연결 시)
        daily_usage = []
        if is_supabase_enabled():
            try:
                from datetime import datetime, timedelta, timezone
                client = __import__('services.supabase_service', fromlist=['get_supabase']).get_supabase()
                week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()[:10]
                result = client.table('ie_usage') \
                    .select('date, used_count') \
                    .eq('user_id', g.user_id) \
                    .gte('date', week_ago) \
                    .order('date', desc=False) \
                    .execute()
                daily_usage = result.data or []
            except Exception:
                pass

        return jsonify({
            'credits': balance,
            'usage': usage,
            'subscription': sub,
            'daily_usage': daily_usage,
        })
    except Exception as e:
        return _payment_exception_response(
            '사용량 대시보드 조회 오류',
            e,
            '[서버 오류] 사용량 정보를 조회할 수 없습니다.'
        )


# =============================================
# 레퍼럴 API (F4-06)
# =============================================

@blog_bp.route('/api/referral/info', methods=['GET'])
@require_auth
def get_referral_info():
    """내 추천 정보 (코드, 추천 횟수, 적립 크레딧)"""
    from services.platform.referral_service import referral_service
    try:
        info = referral_service.get_referral_info(g.user_id)
        return jsonify(info)
    except Exception as e:
        return _payment_exception_response(
            '추천 정보 조회 오류',
            e,
            '[서버 오류] 추천 정보를 조회할 수 없습니다.'
        )


@blog_bp.route('/api/referral/apply', methods=['POST'])
@require_auth
def apply_referral():
    """추천 코드 적용"""
    from services.platform.referral_service import referral_service

    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()
    if not code:
        return error_response('추천 코드를 입력해주세요.')

    try:
        result = referral_service.apply_referral(g.user_id, code)
        if not result.get('success'):
            return _safe_payment_error_response(
                result.get('error'),
                '[서버 오류] 추천 코드 적용에 실패했습니다.',
                400
            )
        return jsonify(result)
    except Exception as e:
        return _payment_exception_response(
            '추천 코드 적용 오류',
            e,
            '[서버 오류] 추천 코드 적용에 실패했습니다.'
        )


# =============================================
# API 키 관리 API (F4-07)
# =============================================

@blog_bp.route('/api/keys', methods=['GET'])
@require_auth
def list_api_keys():
    """사용자 API 키 목록"""
    from services.data.api_key_service import api_key_service
    try:
        keys = api_key_service.list_keys(g.user_id)
        return jsonify({'keys': keys})
    except Exception as e:
        return _payment_exception_response(
            'API 키 목록 조회 오류',
            e,
            '[서버 오류] API 키 목록을 조회할 수 없습니다.'
        )


@blog_bp.route('/api/keys', methods=['POST'])
@require_auth
def create_api_key():
    """새 API 키 발급"""
    from services.data.api_key_service import api_key_service

    data = request.get_json(silent=True) or {}
    name = data.get('name', 'default').strip()
    if not name:
        name = 'default'

    try:
        result = api_key_service.create_key(g.user_id, name)
        if 'error' in result:
            return _safe_payment_error_response(
                result['error'],
                '[서버 오류] API 키 발급에 실패했습니다.',
                500
            )
        return jsonify(result), 201
    except Exception as e:
        return _payment_exception_response(
            'API 키 발급 오류',
            e,
            '[서버 오류] API 키 발급에 실패했습니다.'
        )


@blog_bp.route('/api/keys/<key_id>', methods=['DELETE'])
@require_auth
def revoke_api_key(key_id):
    """API 키 비활성화"""
    from services.data.api_key_service import api_key_service

    if api_key_service.revoke_key(g.user_id, key_id):
        return success_response()
    return error_response('API 키 삭제에 실패했습니다.', 500)


# =============================================
# 인보이스 API (F4-10)
# =============================================

@blog_bp.route('/api/invoices', methods=['GET'])
@require_auth
def list_invoices():
    """사용자 인보이스 목록"""
    from services.payment.invoice_service import invoice_service
    try:
        invoices = invoice_service.list_invoices(g.user_id)
        return jsonify({'invoices': invoices})
    except Exception as e:
        return _payment_exception_response(
            '인보이스 목록 조회 오류',
            e,
            '[서버 오류] 인보이스 목록을 조회할 수 없습니다.'
        )


@blog_bp.route('/api/invoices', methods=['POST'])
@require_auth
def create_invoice():
    """인보이스 생성"""
    from services.payment.invoice_service import invoice_service
    data = request.get_json(silent=True) or {}
    items = data.get('items', [])
    if not items:
        return error_response('items는 필수입니다.')
    try:
        result = invoice_service.create_invoice(g.user_id, items, data.get('currency', 'KRW'))
        if 'error' in result:
            return _safe_payment_error_response(
                result['error'],
                '[서버 오류] 인보이스 생성에 실패했습니다.',
                400
            )
        return jsonify(result), 201
    except Exception as e:
        return _payment_exception_response(
            '인보이스 생성 오류',
            e,
            '[서버 오류] 인보이스 생성에 실패했습니다.'
        )


@blog_bp.route('/api/invoices/<invoice_id>/pay', methods=['POST'])
@require_auth
def pay_invoice(invoice_id):
    """인보이스 결제 처리"""
    from services.payment.invoice_service import invoice_service
    try:
        result = invoice_service.mark_paid(invoice_id)
        if 'error' in result:
            return _safe_payment_error_response(
                result['error'],
                '[서버 오류] 인보이스 결제 처리에 실패했습니다.',
                404
            )
        return jsonify(result)
    except Exception as e:
        return _payment_exception_response(
            '인보이스 결제 처리 오류',
            e,
            '[서버 오류] 인보이스 결제 처리에 실패했습니다.'
        )


# =============================================
# 쿠폰 API (F4-12)
# =============================================

@blog_bp.route('/api/coupons', methods=['GET'])
@require_auth
def list_coupons():
    """쿠폰 목록"""
    from services.payment.coupon_service import coupon_service
    try:
        return jsonify({'coupons': coupon_service.list_coupons()})
    except Exception as e:
        return _payment_exception_response(
            '쿠폰 목록 조회 오류',
            e,
            '[서버 오류] 쿠폰 목록을 조회할 수 없습니다.'
        )


@blog_bp.route('/api/coupons', methods=['POST'])
@require_auth
def create_coupon():
    """쿠폰 생성"""
    from services.payment.coupon_service import coupon_service
    data = request.get_json(silent=True) or {}
    try:
        result = coupon_service.create_coupon(
            code=data.get('code'),
            discount_type=data.get('discount_type', 'percentage'),
            discount_value=float(data.get('discount_value', 10)),
            max_uses=int(data.get('max_uses', 100)),
            expires_at=data.get('expires_at'),
        )
        if 'error' in result:
            return _safe_payment_error_response(
                result['error'],
                '[서버 오류] 쿠폰 생성에 실패했습니다.',
                400
            )
        return jsonify(result), 201
    except Exception as e:
        return _payment_exception_response(
            '쿠폰 생성 오류',
            e,
            '[서버 오류] 쿠폰 생성에 실패했습니다.'
        )


@blog_bp.route('/api/coupons/validate', methods=['POST'])
@require_auth
def validate_coupon():
    """쿠폰 유효성 검증"""
    from services.payment.coupon_service import coupon_service
    data = request.get_json(silent=True) or {}
    code = data.get('code', '')
    if not code:
        return error_response('쿠폰 코드가 필요합니다.')
    try:
        return jsonify(coupon_service.validate_coupon(code))
    except Exception as e:
        return _payment_exception_response(
            '쿠폰 검증 오류',
            e,
            '[서버 오류] 쿠폰 검증에 실패했습니다.'
        )


@blog_bp.route('/api/coupons/redeem', methods=['POST'])
@require_auth
def redeem_coupon():
    """쿠폰 적용"""
    from services.payment.coupon_service import coupon_service
    data = request.get_json(silent=True) or {}
    code = data.get('code', '')
    amount = float(data.get('amount', 0))
    if not code or amount <= 0:
        return error_response('code와 amount는 필수입니다.')
    try:
        result = coupon_service.redeem_coupon(code, g.user_id, amount)
        if 'error' in result:
            return _safe_payment_error_response(
                result['error'],
                '[서버 오류] 쿠폰 적용에 실패했습니다.',
                400
            )
        return jsonify(result)
    except Exception as e:
        return _payment_exception_response(
            '쿠폰 적용 오류',
            e,
            '[서버 오류] 쿠폰 적용에 실패했습니다.'
        )


# =============================================
# 팀 과금 API (F4-08)
# =============================================

@blog_bp.route('/api/team-billing/<team_id>', methods=['GET'])
@require_auth
def get_team_billing(team_id):
    """팀 과금 현황"""
    from services.payment.team_billing_service import team_billing_service
    try:
        result = team_billing_service.get_team_usage(team_id)
        if 'error' in result:
            return _safe_payment_error_response(
                result['error'],
                '[서버 오류] 팀 과금 현황을 조회할 수 없습니다.',
                404
            )
        return jsonify(result)
    except Exception as e:
        return _payment_exception_response(
            '팀 과금 현황 조회 오류',
            e,
            '[서버 오류] 팀 과금 현황을 조회할 수 없습니다.'
        )


@blog_bp.route('/api/team-billing/<team_id>/members', methods=['GET'])
@require_auth
def get_team_member_usage(team_id):
    """팀 멤버별 사용량"""
    from services.payment.team_billing_service import team_billing_service
    try:
        return jsonify({'members': team_billing_service.get_member_usage(team_id)})
    except Exception as e:
        return _payment_exception_response(
            '팀 멤버 사용량 조회 오류',
            e,
            '[서버 오류] 팀 멤버 사용량을 조회할 수 없습니다.'
        )


# =============================================
# Paddle 결제 API (F4-16)
# =============================================

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
        return _payment_exception_response(
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


# =============================================
# 하이브리드 과금 API (F4-11)
# =============================================

@blog_bp.route('/api/billing/setup', methods=['POST'])
@require_auth
def billing_setup():
    """하이브리드 과금 계정 설정"""
    from services.payment.hybrid_billing_service import hybrid_billing_service

    data = request.get_json(silent=True) or {}
    base_credits = data.get('base_credits')
    overage_rate = data.get('overage_rate')

    if base_credits is None or overage_rate is None:
        return error_response('base_credits와 overage_rate가 필요합니다.')

    try:
        result = hybrid_billing_service.setup_account(
            g.user_id,
            int(base_credits),
            float(overage_rate),
        )
        return jsonify(result)
    except Exception as e:
        return _payment_exception_response(
            '과금 계정 설정 오류',
            e,
            '[서버 오류] 과금 계정 설정에 실패했습니다.'
        )


@blog_bp.route('/api/billing/consume', methods=['POST'])
@require_auth
def billing_consume():
    """크레딧 사용 (기본 크레딧 우선 차감)"""
    from services.payment.hybrid_billing_service import hybrid_billing_service

    data = request.get_json(silent=True) or {}
    amount = int(data.get('amount', 1))

    result = hybrid_billing_service.consume(g.user_id, amount)
    if 'error' in result:
        return _safe_payment_error_response(
            result['error'],
            '[서버 오류] 크레딧 사용에 실패했습니다.',
            400
        )
    return jsonify(result)


@blog_bp.route('/api/billing/summary', methods=['GET'])
@require_auth
def billing_summary():
    """과금 요약 조회"""
    from services.payment.hybrid_billing_service import hybrid_billing_service

    result = hybrid_billing_service.get_billing_summary(g.user_id)
    if 'error' in result:
        return _safe_payment_error_response(
            result['error'],
            '[서버 오류] 과금 정보를 조회할 수 없습니다.',
            404
        )
    return jsonify(result)


@blog_bp.route('/api/billing/reset-monthly', methods=['POST'])
@require_auth
def billing_reset_monthly():
    """월간 과금 초기화"""
    from services.payment.hybrid_billing_service import hybrid_billing_service

    result = hybrid_billing_service.reset_monthly(g.user_id)
    if 'error' in result:
        return _safe_payment_error_response(
            result['error'],
            '[서버 오류] 월간 초기화에 실패했습니다.',
            404
        )
    return jsonify(result)


# =============================================
# 암호화폐 결제 API (F4-17)
# =============================================

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
            return _safe_payment_error_response(
                result['error'],
                '[결제 오류] 암호화폐 결제 요청 생성에 실패했습니다.',
                500
            )
        return jsonify(result), 201
    except Exception as e:
        return _payment_exception_response(
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
        return _payment_exception_response(
            '암호화폐 웹훅 처리 오류',
            e,
            '[결제 오류] 웹훅 처리 중 문제가 발생했습니다.'
        )
