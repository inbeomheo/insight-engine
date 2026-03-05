"""
결제 관련 라우트
크레딧, Stripe 결제, 구독, 체험, 사용량, 레퍼럴, API 키
"""
from flask import request, jsonify, g

from routes.blog_routes import blog_bp
from utils.responses import success_response, error_response
from services.supabase_service import require_auth, is_supabase_enabled


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

    result = stripe_service.create_checkout_session(
        user_id=g.user_id,
        price_id=price_id,
        mode='payment',
    )
    if 'error' in result:
        return error_response(result['error'], 500)
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

    result = stripe_service.create_checkout_session(
        user_id=g.user_id,
        price_id=price_id,
        mode=mode,
    )
    if 'error' in result:
        return error_response(result['error'], 500)
    return jsonify(result)


@blog_bp.route('/api/payment/webhook', methods=['POST'])
def stripe_webhook():
    """Stripe Webhook 수신 (서명 검증 포함)"""
    from services.payment.stripe_service import stripe_service

    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature', '')

    result = stripe_service.handle_webhook(payload, sig_header)
    if not result.get('success'):
        return error_response(result.get('error', 'Webhook 처리 실패'), 400)
    return jsonify({'received': True})


# =============================================
# 구독 API (F4-03)
# =============================================

@blog_bp.route('/api/subscription', methods=['GET'])
@require_auth
def get_subscription():
    """현재 구독 정보 조회"""
    from services.payment.subscription_service import subscription_service
    sub = subscription_service.get_subscription(g.user_id)
    return jsonify(sub)


@blog_bp.route('/api/subscription/upgrade', methods=['POST'])
@require_auth
def upgrade_subscription():
    """구독 업그레이드"""
    from services.payment.subscription_service import subscription_service

    data = request.get_json(silent=True) or {}
    new_plan = data.get('plan', 'pro')
    result = subscription_service.upgrade(g.user_id, new_plan)
    if not result.get('success'):
        return error_response(result.get('error', '업그레이드 실패'), 500)
    return jsonify(result)


@blog_bp.route('/api/subscription/cancel', methods=['POST'])
@require_auth
def cancel_subscription():
    """구독 취소"""
    from services.payment.subscription_service import subscription_service
    result = subscription_service.cancel(g.user_id)
    if not result.get('success'):
        return error_response(result.get('error', '취소 실패'), 500)
    return jsonify(result)


# =============================================
# 무료 체험 API (F4-04)
# =============================================

@blog_bp.route('/api/trial/start', methods=['POST'])
@require_auth
def start_trial():
    """7일 무료 체험 시작"""
    from services.payment.trial_service import trial_service
    result = trial_service.start_trial(g.user_id)
    if not result.get('success'):
        if result.get('already_used'):
            return error_response('이미 무료 체험을 사용하셨습니다.', 409)
        return error_response(result.get('error', '체험 시작 실패'), 500)
    return jsonify(result)


@blog_bp.route('/api/trial/status', methods=['GET'])
@require_auth
def get_trial_status():
    """체험 상태 조회"""
    from services.payment.trial_service import trial_service
    trial = trial_service.get_trial(g.user_id)
    active = trial_service.is_trial_active(g.user_id)
    remaining = trial_service.get_remaining_days(g.user_id)
    return jsonify({
        'active': active,
        'remaining_days': remaining,
        'trial_end': trial.get('trial_end', ''),
    })


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


# =============================================
# 레퍼럴 API (F4-06)
# =============================================

@blog_bp.route('/api/referral/info', methods=['GET'])
@require_auth
def get_referral_info():
    """내 추천 정보 (코드, 추천 횟수, 적립 크레딧)"""
    from services.referral_service import referral_service
    info = referral_service.get_referral_info(g.user_id)
    return jsonify(info)


@blog_bp.route('/api/referral/apply', methods=['POST'])
@require_auth
def apply_referral():
    """추천 코드 적용"""
    from services.referral_service import referral_service

    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()
    if not code:
        return error_response('추천 코드를 입력해주세요.')

    result = referral_service.apply_referral(g.user_id, code)
    if not result.get('success'):
        return error_response(result.get('error', '추천 코드 적용 실패'))
    return jsonify(result)


# =============================================
# API 키 관리 API (F4-07)
# =============================================

@blog_bp.route('/api/keys', methods=['GET'])
@require_auth
def list_api_keys():
    """사용자 API 키 목록"""
    from services.api_key_service import api_key_service
    keys = api_key_service.list_keys(g.user_id)
    return jsonify({'keys': keys})


@blog_bp.route('/api/keys', methods=['POST'])
@require_auth
def create_api_key():
    """새 API 키 발급"""
    from services.api_key_service import api_key_service

    data = request.get_json(silent=True) or {}
    name = data.get('name', 'default').strip()
    if not name:
        name = 'default'

    result = api_key_service.create_key(g.user_id, name)
    if 'error' in result:
        return error_response(result['error'], 500)
    return jsonify(result), 201


@blog_bp.route('/api/keys/<key_id>', methods=['DELETE'])
@require_auth
def revoke_api_key(key_id):
    """API 키 비활성화"""
    from services.api_key_service import api_key_service

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
    invoices = invoice_service.list_invoices(g.user_id)
    return jsonify({'invoices': invoices})


@blog_bp.route('/api/invoices', methods=['POST'])
@require_auth
def create_invoice():
    """인보이스 생성"""
    from services.payment.invoice_service import invoice_service
    data = request.get_json(silent=True) or {}
    items = data.get('items', [])
    if not items:
        return error_response('items는 필수입니다.')
    result = invoice_service.create_invoice(g.user_id, items, data.get('currency', 'KRW'))
    if 'error' in result:
        return error_response(result['error'])
    return jsonify(result), 201


@blog_bp.route('/api/invoices/<invoice_id>/pay', methods=['POST'])
@require_auth
def pay_invoice(invoice_id):
    """인보이스 결제 처리"""
    from services.payment.invoice_service import invoice_service
    result = invoice_service.mark_paid(invoice_id)
    if 'error' in result:
        return error_response(result['error'], 404)
    return jsonify(result)


# =============================================
# 쿠폰 API (F4-12)
# =============================================

@blog_bp.route('/api/coupons', methods=['GET'])
def list_coupons():
    """쿠폰 목록"""
    from services.payment.coupon_service import coupon_service
    return jsonify({'coupons': coupon_service.list_coupons()})


@blog_bp.route('/api/coupons', methods=['POST'])
def create_coupon():
    """쿠폰 생성"""
    from services.payment.coupon_service import coupon_service
    data = request.get_json(silent=True) or {}
    result = coupon_service.create_coupon(
        code=data.get('code'),
        discount_type=data.get('discount_type', 'percentage'),
        discount_value=float(data.get('discount_value', 10)),
        max_uses=int(data.get('max_uses', 100)),
        expires_at=data.get('expires_at'),
    )
    if 'error' in result:
        return error_response(result['error'])
    return jsonify(result), 201


@blog_bp.route('/api/coupons/validate', methods=['POST'])
def validate_coupon():
    """쿠폰 유효성 검증"""
    from services.payment.coupon_service import coupon_service
    data = request.get_json(silent=True) or {}
    code = data.get('code', '')
    if not code:
        return error_response('쿠폰 코드가 필요합니다.')
    return jsonify(coupon_service.validate_coupon(code))


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
    result = coupon_service.redeem_coupon(code, g.user_id, amount)
    if 'error' in result:
        return error_response(result['error'])
    return jsonify(result)


# =============================================
# 팀 과금 API (F4-08)
# =============================================

@blog_bp.route('/api/team-billing/<team_id>', methods=['GET'])
def get_team_billing(team_id):
    """팀 과금 현황"""
    from services.payment.team_billing_service import team_billing_service
    result = team_billing_service.get_team_usage(team_id)
    if 'error' in result:
        return error_response(result['error'], 404)
    return jsonify(result)


@blog_bp.route('/api/team-billing/<team_id>/members', methods=['GET'])
def get_team_member_usage(team_id):
    """팀 멤버별 사용량"""
    from services.payment.team_billing_service import team_billing_service
    return jsonify({'members': team_billing_service.get_member_usage(team_id)})
