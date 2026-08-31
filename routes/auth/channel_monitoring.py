"""채널 모니터링 + 운영 대시보드 라우트.

auth_routes.py에서 분리됨. namespace 경유 호출 패턴 유지.
채널 모니터 CRUD는 Channel Monitoring BC (`src/contexts/channel_monitoring/`)
경유로 통합 — 직접 `.table()` 호출 제거.
"""
from flask import g, jsonify
from utils.responses import api_error

from routes import auth_routes as _ar
from routes.auth_routes import auth_bp
from src.contexts.channel_monitoring import (
    delete_channel_monitor as _delete_monitor,
    list_channel_monitors as _list_monitors,
    register_channel_monitor as _register_monitor,
)
from src.contexts.identity.interface.auth_decorators import require_auth


@auth_bp.route('/api/admin/dashboard', methods=['GET'])
@require_auth
def admin_dashboard():
    """운영 대시보드 집계 데이터를 반환합니다."""
    error = _ar._require_admin()
    if error:
        return error

    if not _ar.is_supabase_enabled():
        return api_error('Supabase 미연결', 503)

    try:
        from src.contexts.content_library import fetch_admin_history_stats
        from src.contexts.identity import fetch_daily_usage_history

        # 히스토리 raw 조회 (Content/Library BC) + 가공 (라우트 책임)
        items = fetch_admin_history_stats(days=7)
        total = len(items)
        success_count = sum(1 for i in items if i.get('success', True))

        # 스타일 분포 + 콘텐츠 길이 집계
        style_dist = {}
        total_time = 0
        total_content_length = 0
        content_count = 0
        for item in items:
            s = item.get('style', 'unknown')
            style_dist[s] = style_dist.get(s, 0) + 1
            total_time += float(item.get('elapsed_time', 0) or 0)
            content = item.get('content') or ''
            if content:
                total_content_length += len(content)
                content_count += 1

        avg_time = round(total_time / total, 2) if total > 0 else 0
        avg_content_length = round(total_content_length / content_count) if content_count > 0 else 0

        # 사용량 통계 (Identity BC — admin: account_id=None으로 전체 조회)
        usage_data = fetch_daily_usage_history(account_id=None, days=7)
        daily_usage = [
            {'date': u['date'], 'count': u.get('used_count', 0)}
            for u in usage_data
        ]

        # 가장 많이 사용된 스타일 상위 3개
        top_styles = sorted(style_dist.items(), key=lambda x: x[1], reverse=True)[:3]
        top_styles = [{'style': s, 'count': c} for s, c in top_styles]

        # 가장 생성이 많은 시간대 (0~23시)
        hour_dist = {}
        for item in items:
            created = item.get('created_at', '')
            if created and len(created) >= 13:
                try:
                    hour = int(created[11:13])
                    hour_dist[hour] = hour_dist.get(hour, 0) + 1
                except (ValueError, IndexError):
                    pass
        busiest_hour = max(hour_dist, key=hour_dist.get) if hour_dist else None

        # 최근 5개 생성 기록 (제목 + 스타일)
        sorted_items = sorted(items, key=lambda x: x.get('created_at', ''), reverse=True)
        recent_generations = []
        for item in sorted_items[:5]:
            title = (item.get('content') or '')[:80].split('\n')[0].strip()
            if not title:
                title = '(제목 없음)'
            recent_generations.append({
                'title': title,
                'style': item.get('style', 'unknown'),
                'created_at': item.get('created_at', ''),
            })

        # 프로바이더별 활성 상태 집계 (서버 설정 기반)
        from config import PROVIDER_API_KEYS, SUPPORTED_PROVIDERS
        provider_distribution = {}
        _provider_labels = {
            'cliproxy': 'OPEN AI',
            'zai': 'Z.AI',
        }
        for prov in SUPPORTED_PROVIDERS:
            key = PROVIDER_API_KEYS.get(prov, '')
            if prov == 'cliproxy' and key:
                provider_distribution[_provider_labels.get(prov, prov)] = 'active'
            elif key and key not in ('', 'dummy'):
                provider_distribution[_provider_labels.get(prov, prov)] = 'active'

        return jsonify({
            'period': '7d',
            'total_generations': total,
            'success_rate': round(success_count / total * 100, 1) if total > 0 else 0,
            'avg_time': avg_time,
            'avg_content_length': avg_content_length,
            'style_distribution': style_dist,
            'top_styles': top_styles,
            'daily_usage': daily_usage,
            'recent_generations': recent_generations,
            'busiest_hour': busiest_hour,
            'provider_distribution': provider_distribution,
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Dashboard data failed: {e}")
        return api_error('데이터 조회 실패', 500)


@auth_bp.route('/api/channel-monitors', methods=['GET'])
@require_auth
def get_channel_monitors():
    """사용자 채널 모니터 목록 조회"""
    error = _ar._check_supabase()
    if error:
        return error

    try:
        return jsonify({'monitors': _list_monitors(g.user_id)})
    except Exception as e:
        return _ar._exception_error_response(
            '모니터 조회 오류',
            e,
            '[서버 오류] 모니터 조회 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/channel-monitors', methods=['POST'])
@require_auth
def create_channel_monitor():
    """채널 모니터 등록"""
    error = _ar._check_supabase()
    if error:
        return error

    data = _ar._get_json_data()
    if not (data.get('channel_id') or '').strip():
        return _ar._error_response('채널 ID가 필요합니다.')

    try:
        created = _register_monitor(g.user_id, data)
        # 도메인 검증 실패(잘못된 주기 등)나 저장 실패 시 None — 성공(201)으로
        # 위장하지 않고 명시적 4xx로 응답해 조용한 데이터 손실을 방지한다.
        if created is None:
            return _ar._error_response(
                '채널 모니터를 등록하지 못했습니다. 채널 ID와 폴링 주기 등 입력값을 확인해주세요.'
            )
        return jsonify(created), 201
    except Exception as e:
        return _ar._exception_error_response(
            '모니터 등록 오류',
            e,
            '[서버 오류] 모니터 등록 중 문제가 발생했습니다.'
        )


@auth_bp.route('/api/channel-monitors/<monitor_id>', methods=['DELETE'])
@require_auth
def delete_channel_monitor(monitor_id):
    """채널 모니터 삭제"""
    error = _ar._check_supabase()
    if error:
        return error

    try:
        # 삭제 결과(bool)를 검증 — 실제로 삭제되지 않았는데 성공으로 응답하면
        # 클라이언트가 거짓 양성(false positive)을 받게 되므로 4xx로 응답한다.
        deleted = _delete_monitor(g.user_id, monitor_id)
        if not deleted:
            return _ar._error_response(
                '해당 채널 모니터를 찾을 수 없거나 이미 삭제되었습니다.', 404
            )
        return _ar._success_response()
    except Exception as e:
        return _ar._exception_error_response(
            '모니터 삭제 오류',
            e,
            '[서버 오류] 모니터 삭제 중 문제가 발생했습니다.'
        )
