"""
분석 & 인사이트 라우트 (F6-01 ~ F6-25)
/api/admin/ 하위 엔드포인트 집합
"""
import csv
import io
import json
import threading
import time
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, Response, stream_with_context

from extensions import limiter
from services.supabase_service import require_auth
from services.analytics.dashboard_service import DashboardService
from services.analytics.performance_service import PerformanceService
from services.analytics.cost_tracker_service import CostTrackerService
from services.analytics.ab_test_service import ABTestService
from services.analytics.user_behavior_service import UserBehaviorService
from services.analytics.quality_trend_service import QualityTrendService
from services.analytics.style_performance_service import StylePerformanceService
from services.analytics.model_benchmark_service import ModelBenchmarkService
from services.analytics.realtime_monitor_service import RealtimeMonitorService
from services.analytics.anomaly_service import AnomalyService
from services.analytics.roi_calculator_service import ROICalculatorService
from services.analytics.heatmap_service import HeatmapService
from services.digest_service import DigestService
from services.logging_config import ServiceLogger

logger = ServiceLogger('AnalyticsRoutes')

analytics_bp = Blueprint('analytics', __name__)

# 싱글톤 서비스 인스턴스
_dashboard = DashboardService()
_performance = PerformanceService()
_cost_tracker = CostTrackerService()
_ab_test = ABTestService()
_user_behavior = UserBehaviorService()
_quality_trend = QualityTrendService()
_style_perf = StylePerformanceService()
_model_bench = ModelBenchmarkService()
_realtime = RealtimeMonitorService()
_anomaly = AnomalyService()
_roi = ROICalculatorService()
_heatmap = HeatmapService()
_digest = DigestService()

# 대시보드 공유 링크 저장소 (인메모리)
_share_tokens: dict[str, dict] = {}

# 로그 스트림 버퍼 (SSE용)
_log_buffer: list[str] = []
_log_lock = threading.Lock()
MAX_LOG_BUFFER = 200


def _append_log(message: str) -> None:
    with _log_lock:
        _log_buffer.append(f'{datetime.now(timezone.utc).isoformat()} {message}')
        if len(_log_buffer) > MAX_LOG_BUFFER:
            del _log_buffer[0]


# ─── F6-01: 운영 대시보드 고도화 ─────────────────────────────
@analytics_bp.route('/api/admin/dashboard/extended', methods=['GET'])
@require_auth
def dashboard_extended():
    """운영 대시보드 확장 통계"""
    days = int(request.args.get('days', 30))
    return jsonify({
        'summary': _dashboard.get_summary(days),
        'by_style': _dashboard.get_style_stats(days),
        'by_model': _dashboard.get_model_stats(days),
        'daily_trend': _dashboard.get_daily_trend(days),
    })


@analytics_bp.route('/api/admin/dashboard/record', methods=['POST'])
@require_auth
def dashboard_record():
    """생성 이벤트 기록 (내부 호출용)"""
    data = request.get_json() or {}
    _dashboard.record_generation(
        style=data.get('style', ''),
        model=data.get('model', ''),
        tokens=int(data.get('tokens', 0)),
        duration_ms=float(data.get('duration_ms', 0)),
        success=bool(data.get('success', True)),
    )
    return jsonify({'ok': True})


# ─── F6-02: 콘텐츠 성과 추적 ─────────────────────────────────
@analytics_bp.route('/api/performance/<content_id>', methods=['GET'])
@require_auth
def get_performance(content_id: str):
    return jsonify(_performance.get_metrics(content_id))


@analytics_bp.route('/api/performance/<content_id>/view', methods=['POST'])
@limiter.limit("30/minute")
def record_view(content_id: str):
    _performance.record_view(content_id)
    return jsonify({'ok': True})


@analytics_bp.route('/api/performance/<content_id>/share', methods=['POST'])
@limiter.limit("30/minute")
def record_share(content_id: str):
    _performance.record_share(content_id)
    return jsonify({'ok': True})


@analytics_bp.route('/api/performance/top', methods=['GET'])
@require_auth
def top_contents():
    by = request.args.get('by', 'views')
    limit = int(request.args.get('limit', 10))
    return jsonify(_performance.get_top_contents(by=by, limit=limit))


@analytics_bp.route('/api/performance/aggregate', methods=['GET'])
@require_auth
def performance_aggregate():
    return jsonify(_performance.get_aggregate())


# ─── F6-05: 비용 추적 ─────────────────────────────────────────
@analytics_bp.route('/api/admin/costs', methods=['GET'])
@require_auth
def get_costs():
    days = request.args.get('days')
    days_int = int(days) if days else None
    return jsonify({
        'total': _cost_tracker.get_total_cost(days_int),
        'by_model': _cost_tracker.get_cost_by_model(days_int),
        'daily': _cost_tracker.get_daily_cost(days_int or 30),
    })


# ─── F6-08: ROI 계산기 ───────────────────────────────────────
@analytics_bp.route('/api/admin/roi', methods=['POST'])
@require_auth
def calculate_roi():
    data = request.get_json() or {}
    result = _roi.calculate_roi(
        generation_cost_usd=float(data.get('generation_cost_usd', 0)),
        views=int(data.get('views', 0)),
        clicks=int(data.get('clicks', 0)),
        conversions=int(data.get('conversions', 0)),
        revenue_per_conversion_usd=float(data.get('revenue_per_conversion_usd', 0)),
    )
    return jsonify(result)


# ─── F6-09: 히트맵 ───────────────────────────────────────────
@analytics_bp.route('/api/heatmap/<content_id>/click', methods=['POST'])
@limiter.limit("30/minute")
def record_click(content_id: str):
    data = request.get_json() or {}
    _heatmap.record_click(content_id, int(data.get('x', 0)), int(data.get('y', 0)))
    return jsonify({'ok': True})


@analytics_bp.route('/api/heatmap/<content_id>/scroll', methods=['POST'])
@limiter.limit("30/minute")
def record_scroll(content_id: str):
    data = request.get_json() or {}
    _heatmap.record_scroll(content_id, float(data.get('depth_pct', 0)))
    return jsonify({'ok': True})


@analytics_bp.route('/api/heatmap/<content_id>', methods=['GET'])
@require_auth
def get_heatmap(content_id: str):
    mode = request.args.get('mode', 'click')
    if mode == 'scroll':
        return jsonify(_heatmap.get_scroll_distribution(content_id))
    return jsonify(_heatmap.get_click_heatmap(content_id))


# ─── F6-10: A/B 테스트 ───────────────────────────────────────
@analytics_bp.route('/api/ab-tests', methods=['POST'])
@require_auth
def create_ab_test():
    data = request.get_json() or {}
    name = data.get('name', '')
    variants = data.get('variants', [])
    if not name or len(variants) < 2:
        return jsonify({'error': 'name과 최소 2개 variants 필요'}), 400
    test_id = _ab_test.create_test(name, variants)
    return jsonify({'test_id': test_id})


@analytics_bp.route('/api/ab-tests', methods=['GET'])
@require_auth
def list_ab_tests():
    return jsonify(_ab_test.list_tests())


@analytics_bp.route('/api/ab-tests/<test_id>/results', methods=['GET'])
@require_auth
def ab_test_results(test_id: str):
    return jsonify(_ab_test.get_results(test_id))


@analytics_bp.route('/api/ab-tests/<test_id>/event', methods=['POST'])
@limiter.limit("30/minute")
def ab_test_event(test_id: str):
    data = request.get_json() or {}
    variant = data.get('variant', '')
    event_type = data.get('event_type', 'exposure')
    user_id = data.get('user_id', '')
    if event_type == 'conversion':
        _ab_test.record_conversion(test_id, variant, user_id)
    else:
        _ab_test.record_exposure(test_id, variant, user_id)
    return jsonify({'ok': True})


# ─── F6-11: 사용자 행동 분석 ─────────────────────────────────
@analytics_bp.route('/api/behavior/record', methods=['POST'])
@limiter.limit("30/minute")
def record_behavior():
    data = request.get_json() or {}
    _user_behavior.record(
        feature=data.get('feature', ''),
        action=data.get('action', ''),
        user_id=data.get('user_id', 'anonymous'),
        session_id=data.get('session_id', ''),
    )
    return jsonify({'ok': True})


@analytics_bp.route('/api/admin/behavior/features', methods=['GET'])
@require_auth
def feature_frequency():
    days = int(request.args.get('days', 30))
    return jsonify(_user_behavior.get_feature_frequency(days))


@analytics_bp.route('/api/admin/behavior/sessions', methods=['GET'])
@require_auth
def session_stats():
    return jsonify(_user_behavior.get_session_stats())


# ─── F6-12: 품질 트렌드 ──────────────────────────────────────
@analytics_bp.route('/api/admin/quality/trend', methods=['GET'])
@require_auth
def quality_trend():
    days = int(request.args.get('days', 30))
    granularity = request.args.get('granularity', 'day')
    return jsonify({
        'trend': _quality_trend.get_trend(days, granularity),
        'by_style': _quality_trend.get_style_quality(days),
        'by_model': _quality_trend.get_model_quality(days),
        'overall': _quality_trend.get_overall_stats(),
    })


# ─── F6-13: 스타일별 성과 비교 ───────────────────────────────
@analytics_bp.route('/api/admin/styles/performance', methods=['GET'])
@require_auth
def style_performance():
    return jsonify({
        'comparison': _style_perf.get_comparison(),
        'top': _style_perf.get_top_style(),
    })


# ─── F6-14: 모델별 성능 비교 ─────────────────────────────────
@analytics_bp.route('/api/admin/models/benchmark', methods=['GET'])
@require_auth
def model_benchmark():
    metric = request.args.get('metric', 'avg_quality')
    return jsonify({
        'benchmark': _model_bench.get_benchmark(),
        'ranked': _model_bench.rank_by(metric),
    })


# ─── F6-15: 실시간 모니터링 ──────────────────────────────────
@analytics_bp.route('/api/admin/realtime/status', methods=['GET'])
@require_auth
def realtime_status():
    return jsonify({
        'status': _realtime.get_status(),
        'recent_errors': _realtime.get_recent_errors(10),
    })


# ─── F6-16: 이상 탐지 ────────────────────────────────────────
@analytics_bp.route('/api/admin/anomalies', methods=['GET'])
@require_auth
def get_anomalies():
    limit = int(request.args.get('limit', 50))
    return jsonify(_anomaly.get_anomalies(limit))


@analytics_bp.route('/api/admin/anomalies/metric', methods=['POST'])
@require_auth
def record_metric():
    data = request.get_json() or {}
    result = _anomaly.record_metric(
        metric=data.get('metric', ''),
        value=float(data.get('value', 0)),
    )
    return jsonify({'anomaly': result})


# ─── F6-18: 데이터 내보내기 ──────────────────────────────────
@analytics_bp.route('/api/admin/export-data', methods=['GET'])
@require_auth
def export_data():
    """대시보드 데이터를 CSV 또는 JSON으로 내보내기"""
    fmt = request.args.get('format', 'json')
    days = int(request.args.get('days', 30))

    data = {
        'summary': _dashboard.get_summary(days),
        'by_style': _dashboard.get_style_stats(days),
        'by_model': _dashboard.get_model_stats(days),
        'daily_trend': _dashboard.get_daily_trend(days),
        'costs': _cost_tracker.get_cost_by_model(days),
    }

    if fmt == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        # 일별 트렌드 CSV
        writer.writerow(['date', 'count'])
        for row in data['daily_trend']:
            writer.writerow([row['date'], row['count']])
        csv_content = output.getvalue()
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=dashboard_{days}d.csv'},
        )

    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename=dashboard_{days}d.json'},
    )


# ─── F6-23: 주간 다이제스트 ──────────────────────────────────
@analytics_bp.route('/api/admin/digest', methods=['POST'])
@require_auth
def generate_digest():
    data = request.get_json() or {}
    generations = data.get('generations', [])
    period_days = int(data.get('period_days', 7))
    digest = _digest.build_digest(generations, period_days)
    fmt = data.get('format', 'json')
    if fmt == 'text':
        return jsonify({'digest': _digest.to_text(digest)})
    if fmt == 'html':
        return jsonify({'digest': _digest.to_html(digest)})
    return jsonify(digest)


# ─── F6-24: 대시보드 공유 링크 ───────────────────────────────
@analytics_bp.route('/api/dashboard/share', methods=['POST'])
@require_auth
def create_share_link():
    import uuid
    token = str(uuid.uuid4())
    days = int(request.get_json().get('days', 30) if request.get_json() else 30)
    _share_tokens[token] = {
        'days': days,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'expires_at': time.time() + 86400,
    }
    return jsonify({'share_url': f'/api/dashboard/shared/{token}', 'token': token})


@analytics_bp.route('/api/dashboard/shared/<token>', methods=['GET'])
def view_shared_dashboard(token: str):
    meta = _share_tokens.get(token)
    if not meta or time.time() > meta.get('expires_at', 0):
        _share_tokens.pop(token, None)
        return jsonify({'error': '만료된 링크'}), 404
    days = meta['days']
    return jsonify({
        'shared': True,
        'created_at': meta['created_at'],
        'summary': _dashboard.get_summary(days),
        'by_style': _dashboard.get_style_stats(days),
        'daily_trend': _dashboard.get_daily_trend(days),
    })


# ─── F6-25: 실시간 로그 뷰어 (SSE) ──────────────────────────
@analytics_bp.route('/api/logs/stream', methods=['GET'])
@require_auth
def log_stream():
    """SSE 실시간 로그 스트림"""
    def generate():
        last_idx = 0
        while True:
            with _log_lock:
                new_logs = _log_buffer[last_idx:]
                last_idx = len(_log_buffer)
            for log in new_logs:
                yield f'data: {json.dumps({"log": log})}\n\n'
            time.sleep(1)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


@analytics_bp.route('/api/logs/recent', methods=['GET'])
@require_auth
def recent_logs():
    """최근 로그 반환"""
    limit = int(request.args.get('limit', 50))
    with _log_lock:
        logs = _log_buffer[-limit:]
    return jsonify({'logs': logs})
