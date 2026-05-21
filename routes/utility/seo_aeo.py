"""SEO/AEO/EEAT/구조화 데이터 라우트 — utility_routes.py에서 분리."""
from flask import jsonify, request

from routes.blog_routes import blog_bp
from utils.responses import handle_error


# ── FAQ 생성 ──────────────────────────────────────────

@blog_bp.route('/api/generate-faq', methods=['POST'])
def generate_faq_route():
    """콘텐츠 기반 FAQ를 자동 생성합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        max_questions = data.get('max_questions', 5)

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.content.faq_generator_service import generate_faq
        result = generate_faq(content, max_questions)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, 'FAQ 생성')


# ── AI 답변 엔진 최적화 ──────────────────────────────

@blog_bp.route('/api/analyze-aeo', methods=['POST'])
def analyze_aeo_route():
    """AI 검색엔진 답변 인용 가능성을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        target_query = data.get('target_query', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.aeo_optimizer_service import analyze_aeo
        result = analyze_aeo(content, target_query)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, 'AEO 분석')


# ── 검색 의도 분석 ──────────────────────────────────

@blog_bp.route('/api/search-intent', methods=['POST'])
def search_intent_route():
    """콘텐츠의 검색 의도 적합도를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        target_keyword = data.get('target_keyword', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.search_intent_service import analyze_search_intent
        result = analyze_search_intent(content, target_keyword)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '검색 의도 분석')


# ── 내부 링크 기회 탐지 ──────────────────────────────

@blog_bp.route('/api/internal-links', methods=['POST'])
def internal_links_route():
    """여러 콘텐츠 간 내부 링크 기회를 탐지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        contents = data.get('contents', [])
        current_content = data.get('current_content', '')

        if not contents or len(contents) < 2:
            return jsonify({'error': '최소 2개 콘텐츠가 필요합니다. contents: [{id, title, content}, ...]'}), 400

        from services.seo.internal_link_service import find_link_opportunities
        result = find_link_opportunities(contents, current_content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '내부 링크 탐지')


# ── 독창성 검사 ──────────────────────────────────────

@blog_bp.route('/api/check-originality', methods=['POST'])
def check_originality_route():
    """콘텐츠의 독창성과 중복 리스크를 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        reference_contents = data.get('reference_contents', None)

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.originality_checker_service import check_originality
        result = check_originality(content, reference_contents)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '독창성 검사')


# ── 토픽 갭 분석 ────────────────────────────────────

@blog_bp.route('/api/topic-gaps', methods=['POST'])
def topic_gaps_route():
    """현재 콘텐츠와 참고 콘텐츠를 비교하여 빠진 주제를 찾습니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        reference_contents = data.get('reference_contents', None)

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.topic_gap_service import analyze_topic_gaps
        result = analyze_topic_gaps(content, reference_contents)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '토픽 갭 분석')


# ── E-E-A-T 신뢰 신호 분석 ──────────────────────────

@blog_bp.route('/api/analyze-eeat', methods=['POST'])
def analyze_eeat_route():
    """콘텐츠의 E-E-A-T 신뢰 신호를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        author_info = data.get('author_info', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.eeat_analyzer_service import analyze_eeat
        result = analyze_eeat(content, author_info)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, 'E-E-A-T 분석')


# ── SERP 기능 기회 분석 ──────────────────────────────

@blog_bp.route('/api/serp-features', methods=['POST'])
def serp_features_route():
    """SERP 특수 기능 노출 가능성을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        target_keyword = data.get('target_keyword', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.serp_feature_service import analyze_serp_features
        result = analyze_serp_features(content, target_keyword)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, 'SERP 기능 분석')


# ── 토픽 클러스터 매핑 ──────────────────────────────

@blog_bp.route('/api/topic-clusters', methods=['POST'])
def topic_clusters_route():
    """콘텐츠 목록의 토픽 클러스터 구조를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        contents = data.get('contents', [])

        if not contents or not isinstance(contents, list):
            return jsonify({'error': '분석할 콘텐츠 목록(contents)이 필요합니다.'}), 400

        from services.seo.topic_cluster_service import map_topic_clusters
        result = map_topic_clusters(contents)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '토픽 클러스터 분석')


# ── 엔터티 커버리지 분석 ──────────────────────────────

@blog_bp.route('/api/analyze-entities', methods=['POST'])
def analyze_entities_route():
    """콘텐츠의 엔터티 커버리지를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.entity_coverage_service import analyze_entities
        result = analyze_entities(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '엔터티 분석')


# ── 주장/인용 검증 ──────────────────────────────

@blog_bp.route('/api/verify-claims', methods=['POST'])
def verify_claims_route():
    """콘텐츠의 사실 주장과 인용 출처를 검증합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.claim_verifier_service import verify_claims
        result = verify_claims(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '주장/인용 검증')


# ── 스키마 기회 탐색 ──────────────────────────────

@blog_bp.route('/api/schema-opportunities', methods=['POST'])
def schema_opportunities_route():
    """콘텐츠의 구조화 데이터(JSON-LD) 적용 기회를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.schema_opportunity_service import find_schema_opportunities
        result = find_schema_opportunities(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '스키마 기회 분석')


# ── 앵커 텍스트 품질 감사 ──────────────────────────────

@blog_bp.route('/api/audit-anchors', methods=['POST'])
def audit_anchors_route():
    """콘텐츠 내 링크의 앵커 텍스트 품질을 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.anchor_text_service import audit_anchor_texts
        result = audit_anchor_texts(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '앵커 텍스트 감사')


# ── 약속 이행 감사 ──────────────────────────────

@blog_bp.route('/api/audit-promises', methods=['POST'])
def audit_promises_route():
    """제목/소제목의 약속이 본문에서 이행되는지 검증합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.promise_match_service import audit_promise_match
        result = audit_promise_match(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '약속 이행 감사')


# ── 내부 일관성 검사 ──────────────────────────────

@blog_bp.route('/api/check-consistency', methods=['POST'])
def check_consistency_route():
    """콘텐츠 내부의 수치/날짜/비교 모순을 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.consistency_checker_service import check_consistency
        result = check_consistency(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '일관성 검사')


# ── 소제목 간격 분석 ──────────────────────────────

@blog_bp.route('/api/detect-subheading-gaps', methods=['POST'])
def detect_subheading_gaps_route():
    """헤딩 사이 텍스트 길이와 섹션 균형을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.subheading_gap_service import detect_subheading_gaps
        result = detect_subheading_gaps(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '소제목 간격 분석')


@blog_bp.route('/api/detect-actionability-gaps', methods=['POST'])
def detect_actionability_gaps_route():
    """실행 가능성 갭 감지 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.actionability_gap_service import detect_actionability_gaps
        result = detect_actionability_gaps(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '실행 가능성 갭 감지')


@blog_bp.route('/api/detect-list-table-opportunities', methods=['POST'])
def detect_list_table_opportunities_route():
    """목록/표 변환 기회 감지 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.list_table_opportunity_service import detect_list_table_opportunities
        result = detect_list_table_opportunities(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '목록/표 변환 기회 감지')


@blog_bp.route('/api/audit-image-seo', methods=['POST'])
def audit_image_seo_route():
    """이미지 SEO 점검 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.image_seo_auditor_service import audit_image_seo
        result = audit_image_seo(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '이미지 SEO 점검')


@blog_bp.route('/api/audit-source-diversity', methods=['POST'])
def audit_source_diversity_route():
    """외부 소스 다양성 점검 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.external_source_diversity_service import audit_external_source_diversity
        result = audit_external_source_diversity(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '외부 소스 다양성 점검')


@blog_bp.route('/api/detect-chapter-breakpoints', methods=['POST'])
def detect_chapter_breakpoints_route():
    """챕터 분할점 감지 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.transcript.chapter_breakpoint_service import detect_chapter_breakpoints
        result = detect_chapter_breakpoints(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '챕터 분할점 감지')


@blog_bp.route('/api/analyze-question-density', methods=['POST'])
def analyze_question_density_route():
    """질문 밀도 분석 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.question_density_service import analyze_question_density
        result = analyze_question_density(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '질문 밀도 분석')


# ── Meta Description Quality Checker ──
@blog_bp.route('/api/check-meta-description-quality', methods=['POST'])
def check_meta_description_quality_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.meta_description_quality_service import check_meta_description_quality
        result = check_meta_description_quality(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '메타 디스크립션 품질 검사')


# ── Table of Contents Generator ──
@blog_bp.route('/api/generate-toc', methods=['POST'])
def generate_toc_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.content.toc_generator_service import generate_toc
        max_depth = data.get('max_depth', 3)
        result = generate_toc(content, max_depth=max_depth)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '목차 생성')


# ── Article Format Template Checker ──
@blog_bp.route('/api/check-article-format', methods=['POST'])
def check_article_format_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.content.article_format_template_service import check_article_format
        result = check_article_format(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '글 형식 템플릿 검사')


# ── Title Tag Length Checker ──
@blog_bp.route('/api/check-title-tag-length', methods=['POST'])
def check_title_tag_length_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.title_tag_length_service import check_title_tag_length
        result = check_title_tag_length(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '제목 태그 길이 검사')


# ── Keyword Stuffing Detector ──
@blog_bp.route('/api/detect-keyword-stuffing', methods=['POST'])
def detect_keyword_stuffing_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.keyword_stuffing_detector_service import detect_keyword_stuffing
        result = detect_keyword_stuffing(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '키워드 스터핑 감지')


# ── URL Health Checker ──
@blog_bp.route('/api/check-url-health', methods=['POST'])
def check_url_health_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.url_health_checker_service import check_url_health
        result = check_url_health(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, 'URL 건강 검사')


# ── Data Visualization Opportunity ──
@blog_bp.route('/api/find-visualization-opportunities', methods=['POST'])
def find_visualization_opportunities_route():
    """데이터 시각화 기회를 찾습니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.data_visualization_opportunity_service import find_visualization_opportunities
        result = find_visualization_opportunities(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '데이터 시각화 기회 분석')


# ── Question-Answer Closure Checker ──────────────────────────────────
@blog_bp.route('/api/check-qa-closure', methods=['POST'])
def check_qa_closure_route():
    """질문-답변 완결성을 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.qa_closure_service import check_qa_closure
        result = check_qa_closure(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '질문-답변 완결성 검사')


# ── Example Coverage Analyzer ────────────────────────────────────────
@blog_bp.route('/api/analyze-example-coverage', methods=['POST'])
def analyze_example_coverage_route():
    """주장/조언의 예시·근거 커버리지를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.example_coverage_service import analyze_example_coverage
        result = analyze_example_coverage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '예시 커버리지 분석')
