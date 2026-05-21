"""채널 모니터링 + 운영 대시보드 라우트.

auth_routes.py에서 분리됨. namespace 경유 호출 패턴 유지.
"""
from flask import g, jsonify, request

from routes import auth_routes as _ar
from routes.auth_routes import auth_bp
from services.data.supabase_service import require_auth


@auth_bp.route('/api/admin/dashboard', methods=['GET'])
@require_auth
def admin_dashboard():
    """운영 대시보드 집계 데이터를 반환합니다."""
    error = _ar._require_admin()
    if error:
        return error

    if not _ar.is_supabase_enabled():
        return jsonify({'error': 'Supabase 미연결'}), 503

    supabase = _ar.get_supabase()
    if not supabase:
        return jsonify({'error': 'Supabase 연결 실패'}), 503

    try:
        from datetime import datetime, timedelta, timezone
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        # 히스토리 통계
        histories = supabase.table('ie_histories') \
            .select('created_at,style,elapsed_time,success,content') \
            .gte('created_at', week_ago) \
            .execute()

        items = histories.data or []
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

        # 사용량 통계
        usage_data = supabase.table('ie_usage') \
            .select('date,used_count') \
            .gte('date', week_ago[:10]) \
            .order('date', desc=True) \
            .execute()

        daily_usage = [
            {'date': u['date'], 'count': u.get('used_count', 0)}
            for u in (usage_data.data or [])
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
        from config import PROVIDER_API_KEYS
        provider_distribution = {}
        _provider_labels = {
            'gemini': 'Gemini', 'deepseek': 'DeepSeek', 'zhipuai': 'Zhipu AI',
            'ollama': 'Ollama', 'openai': 'OpenAI', 'anthropic': 'Anthropic',
            'openrouter': 'OpenRouter', 'chatmock': 'ChatMock',
        }
        for prov, key in PROVIDER_API_KEYS.items():
            if key and key not in ('', 'dummy', 'http://localhost:11434'):
                provider_distribution[_provider_labels.get(prov, prov)] = 'active'
            elif prov == 'ollama' and key:
                provider_distribution[_provider_labels.get(prov, prov)] = 'local'

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
        return jsonify({'error': '데이터 조회 실패'}), 500


@auth_bp.route('/api/channel-monitors', methods=['GET'])
@require_auth
def get_channel_monitors():
    """사용자 채널 모니터 목록 조회"""
    error = _ar._check_supabase()
    if error:
        return error

    try:
        client = _ar.get_supabase()
        result = client.table('ie_channel_monitors') \
            .select('*') \
            .eq('user_id', g.user_id) \
            .order('created_at', desc=True) \
            .execute()
        return jsonify({'monitors': result.data or []})
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
    channel_id = data.get('channel_id', '').strip()
    if not channel_id:
        return _ar._error_response('채널 ID가 필요합니다.')

    try:
        client = _ar.get_supabase()
        row = {
            'user_id': g.user_id,
            'channel_id': channel_id,
            'channel_title': data.get('channel_title', ''),
            'style_id': data.get('style_id', 'blog_seo'),
            'modifiers': data.get('modifiers', {
                'length': 'medium',
                'writing_style': 'conversational',
                'language': 'ko',
            }),
            'interval_minutes': data.get('interval_minutes', 30),
            'is_active': True,
        }
        result = client.table('ie_channel_monitors').insert(row).execute()
        return jsonify(result.data[0] if result.data else {}), 201
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
        client = _ar.get_supabase()
        client.table('ie_channel_monitors') \
            .delete() \
            .eq('id', monitor_id) \
            .eq('user_id', g.user_id) \
            .execute()
        return _ar._success_response()
    except Exception as e:
        return _ar._exception_error_response(
            '모니터 삭제 오류',
            e,
            '[서버 오류] 모니터 삭제 중 문제가 발생했습니다.'
        )
