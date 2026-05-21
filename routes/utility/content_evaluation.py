"""콘텐츠 종합 평가 라우트 (등급/헤드라인/퀴즈/토론/CTA/성과 예측 등) — utility_routes.py에서 분리."""
from flask import jsonify, request

from routes.blog_routes import blog_bp
from services.data.supabase_service import require_auth
from utils.responses import handle_error


# ── 콘텐츠 종합 등급 평가 ──────────────────────────────

@blog_bp.route('/api/grade-content', methods=['POST'])
def grade_content_route():
    """콘텐츠를 종합 평가하여 A~F 등급을 반환합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '평가할 콘텐츠가 필요합니다.'}), 400

        from services.quality.content_grader_service import grade_content
        result = grade_content(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '콘텐츠 등급 평가')


# ── 스마트 헤드라인 최적화 ──────────────────────────────

@blog_bp.route('/api/optimize-headline', methods=['POST'])
def optimize_headline_route():
    """제목을 분석하고 최적화 제안을 반환합니다."""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', '')
        content = data.get('content', '')

        if not title or not title.strip():
            return jsonify({'error': '분석할 제목이 필요합니다.'}), 400

        from services.seo.headline_optimizer_service import optimize_headline
        result = optimize_headline(title, content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '헤드라인 최적화')


# ── 콘텐츠 신선도 모니터링 ──────────────────────────────

@blog_bp.route('/api/freshness-check', methods=['POST'])
def freshness_check_route():
    """콘텐츠의 신선도를 평가합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        published_date = data.get('published_date', '')

        if not content or not content.strip():
            return jsonify({'error': '평가할 콘텐츠가 필요합니다.'}), 400
        if not published_date:
            return jsonify({'error': '발행일(published_date)이 필요합니다. ISO 8601 형식 (예: 2025-06-15)'}), 400

        from services.seo.freshness_monitor_service import check_freshness
        result = check_freshness(content, published_date)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '콘텐츠 신선도 체크')


# ── 인터랙티브 퀴즈 생성 ──────────────────────────────

@blog_bp.route('/api/generate-quiz', methods=['POST'])
def generate_quiz_route():
    """콘텐츠에서 퀴즈를 자동 생성합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        count = data.get('count', 5)

        if not content or not content.strip():
            return jsonify({'error': '퀴즈를 생성할 콘텐츠가 필요합니다.'}), 400

        from services.content.quiz_generator_service import generate_quiz
        result = generate_quiz(content, count)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '퀴즈 생성')


# ── 콘텐츠 카니발리제이션 감지 ──────────────────────────

@blog_bp.route('/api/check-cannibalization', methods=['POST'])
def check_cannibalization_route():
    """여러 콘텐츠 간의 키워드 카니발리제이션을 감지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        contents = data.get('contents', [])

        if not contents or len(contents) < 2:
            return jsonify({'error': '최소 2개 콘텐츠가 필요합니다. contents: [{id, title, content}, ...]'}), 400

        from services.seo.cannibalization_service import detect_cannibalization
        result = detect_cannibalization(contents)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '카니발리제이션 감지')


# ── AI 토론 생성 ──────────────────────────────────────

@blog_bp.route('/api/generate-debate', methods=['POST'])
def generate_debate_route():
    """주제에 대한 다각적 관점(찬성/반대/중립)을 생성합니다."""
    try:
        data = request.get_json(silent=True) or {}
        topic = data.get('topic', '')
        content = data.get('content', '')

        if not topic or not topic.strip():
            return jsonify({'error': '토론 주제가 필요합니다.'}), 400

        from services.content.debate_service import generate_debate
        result = generate_debate(topic, content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '토론 생성')


# ── 콘텐츠 감성 분석 ──────────────────────────────────

@blog_bp.route('/api/analyze-sentiment', methods=['POST'])
def analyze_sentiment_route():
    """콘텐츠의 감성 톤(긍정/부정/중립)을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentiment_analyzer_service import analyze_sentiment
        result = analyze_sentiment(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '감성 분석')


# ── 훅 문장 생성 ──────────────────────────────────────

@blog_bp.route('/api/generate-hooks', methods=['POST'])
def generate_hooks_route():
    """주제에 대한 훅(서두) 문장을 생성합니다."""
    try:
        data = request.get_json(silent=True) or {}
        topic = data.get('topic', '')
        content = data.get('content', '')
        count = data.get('count', 5)

        if not topic or not topic.strip():
            return jsonify({'error': '주제(topic)가 필요합니다.'}), 400

        from services.content.hook_generator_service import generate_hooks
        result = generate_hooks(topic, content, count)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '훅 생성')


# ── 소셜 프루프 스니펫 추출 ────────────────────────────

@blog_bp.route('/api/extract-snippets', methods=['POST'])
def extract_snippets_route():
    """콘텐츠에서 소셜 공유용 스니펫을 추출합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        max_count = data.get('max_count', 10)

        if not content or not content.strip():
            return jsonify({'error': '스니펫을 추출할 콘텐츠가 필요합니다.'}), 400

        from services.media.social_proof_service import extract_snippets
        result = extract_snippets(content, max_count)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '스니펫 추출')


# ── 가독성 벤치마크 ────────────────────────────────────

@blog_bp.route('/api/benchmark-readability', methods=['POST'])
def benchmark_readability_route():
    """콘텐츠 가독성을 카테고리 벤치마크와 비교합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        category = data.get('category', 'blog')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.readability_benchmark_service import benchmark_readability
        result = benchmark_readability(content, category)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '가독성 벤치마크')


# ── 콘텐츠 아웃라인 생성 ───────────────────────────────

@blog_bp.route('/api/generate-outline', methods=['POST'])
def generate_outline_route():
    """주제에 맞는 콘텐츠 아웃라인을 생성합니다."""
    try:
        data = request.get_json(silent=True) or {}
        topic = data.get('topic', '')
        template = data.get('template', 'guide')
        keywords = data.get('keywords', [])

        if not topic or not topic.strip():
            return jsonify({'error': '주제(topic)가 필요합니다.'}), 400

        from services.content.outline_generator_service import generate_outline
        result = generate_outline(topic, template, keywords)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '아웃라인 생성')


# ── 읽기 시간 예측 ─────────────────────────────────────

@blog_bp.route('/api/reading-time', methods=['POST'])
def reading_time_route():
    """콘텐츠의 읽기 시간과 난이도를 예측합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        content_type = data.get('content_type', 'general')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.reading_time_service import estimate_reading_time
        result = estimate_reading_time(content, content_type)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '읽기 시간 예측')


# ── CTA 분석 ─────────────────────────────────────────

@blog_bp.route('/api/analyze-cta', methods=['POST'])
def analyze_cta_route():
    """콘텐츠의 CTA를 감지하고 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        goal = data.get('goal', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.cta_optimizer_service import analyze_ctas, suggest_ctas
        analysis = analyze_ctas(content)
        if goal:
            suggestions = suggest_ctas(content, goal)
            analysis['goal_suggestions'] = suggestions
        return jsonify(analysis)

    except Exception as e:
        return handle_error(e, 'CTA 분석')


# ── 콘텐츠 성과 예측 ─────────────────────────────────

@blog_bp.route('/api/predict-performance', methods=['POST'])
def predict_performance_route():
    """콘텐츠의 성과(조회수, 참여도)를 예측합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        title = data.get('title', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.content_performance_predictor_service import predict_performance
        result = predict_performance(content, title)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '콘텐츠 성과 예측')


@blog_bp.route('/api/score-content-depth', methods=['POST'])
def score_content_depth_route():
    """콘텐츠 심도 측정 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.content_depth_scorer_service import score_content_depth
        result = score_content_depth(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '콘텐츠 심도 측정')


# ── Conclusion Strength Analyzer ──
@blog_bp.route('/api/analyze-conclusion-strength', methods=['POST'])
def analyze_conclusion_strength_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.conclusion_strength_service import analyze_conclusion_strength
        result = analyze_conclusion_strength(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '결론 강도 분석')


# ── Content Freshness Indicator ──
@blog_bp.route('/api/check-content-freshness', methods=['POST'])
def check_content_freshness_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.content_freshness_indicator_service import check_content_freshness
        result = check_content_freshness(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '콘텐츠 시의성 평가')


@blog_bp.route('/api/score-content-scanability', methods=['POST'])
def score_content_scanability_route():
    """콘텐츠 스캔 가독성을 평가합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.content_scanability_service import score_content_scanability
        result = score_content_scanability(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '스캔 가독성 평가')
