"""문장/단락/연결어/구조 분석 라우트 — utility_routes.py에서 분리."""
from flask import jsonify, request

from routes.blog_routes import blog_bp
from services.data.supabase_service import require_auth
from utils.responses import handle_error


# ── 키워드 밀도 분석 ──────────────────────────────────

@blog_bp.route('/api/keyword-density', methods=['POST'])
def keyword_density_route():
    """콘텐츠의 키워드 밀도를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        keywords = data.get('keywords', None)

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        if keywords:
            from services.seo.keyword_density_service import analyze_density
            result = analyze_density(content, keywords)
        else:
            from services.seo.keyword_density_service import get_density_report
            result = get_density_report(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '키워드 밀도 분석')


# ── 연결어 분석 ───────────────────────────────────────

@blog_bp.route('/api/analyze-transitions', methods=['POST'])
def analyze_transitions_route():
    """콘텐츠의 연결어 사용을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        suggest = data.get('suggest', False)

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.transition_analyzer_service import analyze_transitions, suggest_transitions
        result = analyze_transitions(content)
        if suggest:
            result['recommendations'] = suggest_transitions(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '연결어 분석')


# ── 문단 균형 분석 ────────────────────────────────────

@blog_bp.route('/api/paragraph-balance', methods=['POST'])
def paragraph_balance_route():
    """문단 길이 균형을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.paragraph_balance_service import analyze_balance
        result = analyze_balance(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문단 균형 분석')


# ── 문장 다양성 분석 ──────────────────────────────────

@blog_bp.route('/api/sentence-variety', methods=['POST'])
def sentence_variety_route():
    """문장 길이/구조 다양성을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import analyze_variety
        result = analyze_variety(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문장 다양성 분석')


# ── 헤딩 병렬성 검사 ──────────────────────────────

@blog_bp.route('/api/check-heading-parallelism', methods=['POST'])
def check_heading_parallelism_route():
    """동일 레벨 헤딩의 문법 형태 일관성을 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.heading_parallelism_service import check_heading_parallelism
        result = check_heading_parallelism(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '헤딩 병렬성 검사')


# ── Pronoun Clarity Checker ──────────────────────────────────────────
@blog_bp.route('/api/check-pronoun-clarity', methods=['POST'])
def check_pronoun_clarity_route():
    """대명사 명확성을 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.pronoun_clarity_service import check_pronoun_clarity
        result = check_pronoun_clarity(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '대명사 명확성 검사')


# ── Clause Overload Detector ─────────────────────────────────────────
@blog_bp.route('/api/detect-clause-overload', methods=['POST'])
def detect_clause_overload_route():
    """문장 내 절 과부하를 감지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.clause_overload_service import detect_clause_overload
        result = detect_clause_overload(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '절 과부하 감지')


# ── Heading Term Placement Auditor ───────────────────────────────────
@blog_bp.route('/api/audit-heading-terms', methods=['POST'])
def audit_heading_terms_route():
    """핵심 용어의 헤딩 배치를 점검합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.heading_term_placement_service import audit_heading_term_placement
        result = audit_heading_term_placement(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '헤딩 용어 배치 점검')


# ── Acronym Expansion Compliance Checker ─────────────────────────────
@blog_bp.route('/api/check-acronym-expansion', methods=['POST'])
def check_acronym_expansion_route():
    """약어의 첫 등장 시 풀어쓰기 여부를 점검합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.acronym_expansion_service import check_acronym_expansion
        result = check_acronym_expansion(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '약어 풀어쓰기 점검')


@blog_bp.route('/api/check-paragraph-opening-variety', methods=['POST'])
def check_paragraph_opening_variety_route():
    """문단 시작 다양성 점검 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.paragraph_opening_variety_service import check_paragraph_opening_variety
        result = check_paragraph_opening_variety(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문단 시작 다양성 점검')


@blog_bp.route('/api/check-tone-consistency', methods=['POST'])
def check_tone_consistency_route():
    """문체 일관성 점검 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.tone_consistency_service import check_tone_consistency
        result = check_tone_consistency(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문체 일관성 점검')


@blog_bp.route('/api/detect-linking-verb-overuse', methods=['POST'])
def detect_linking_verb_overuse_route():
    """연결 동사 과다 사용 감지 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.linking_verb_overuse_service import detect_linking_verb_overuse
        result = detect_linking_verb_overuse(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '연결 동사 과다 사용 감지')


# ── Sentence Connector Variety Analyzer ──
@blog_bp.route('/api/analyze-connector-variety', methods=['POST'])
def analyze_connector_variety_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import analyze_connector_variety
        result = analyze_connector_variety(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '연결어 다양성 분석')


# ── Sentence Length Rhythm Analyzer ──
@blog_bp.route('/api/analyze-sentence-rhythm', methods=['POST'])
def analyze_sentence_rhythm_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import analyze_sentence_rhythm
        result = analyze_sentence_rhythm(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문장 리듬 분석')


# ── Sentence Ending Variety ──
@blog_bp.route('/api/analyze-sentence-ending-variety', methods=['POST'])
def analyze_sentence_ending_variety_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import analyze_sentence_ending_variety
        result = analyze_sentence_ending_variety(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '종결어미 다양성 분석')


# ── Passive Construction Ratio ──
@blog_bp.route('/api/analyze-passive-ratio', methods=['POST'])
def analyze_passive_ratio_route():
    """피동/수동 구문 비율을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.passive_construction_ratio_service import analyze_passive_ratio
        result = analyze_passive_ratio(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '피동 구문 비율 분석')


# ── Average Words Per Sentence ──
@blog_bp.route('/api/analyze-avg-words-per-sentence', methods=['POST'])
def analyze_avg_words_per_sentence_route():
    """문장당 평균 단어 수를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import analyze_avg_words_per_sentence
        result = analyze_avg_words_per_sentence(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문장당 평균 단어 수 분석')


# ── Acronym Consistency Checker ──
@blog_bp.route('/api/check-acronym-consistency', methods=['POST'])
def check_acronym_consistency_route():
    """약어 일관성을 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.acronym_consistency_checker_service import check_acronym_consistency
        result = check_acronym_consistency(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '약어 일관성 검사')


# ── Heading Keyword Density ──
@blog_bp.route('/api/analyze-heading-keyword-density', methods=['POST'])
def analyze_heading_keyword_density_route():
    """헤딩 키워드 밀도를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.heading_keyword_density_service import analyze_heading_keyword_density
        result = analyze_heading_keyword_density(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '헤딩 키워드 밀도 분석')


# ── Content Symmetry Analyzer ──
@blog_bp.route('/api/analyze-content-symmetry', methods=['POST'])
def analyze_content_symmetry_route():
    """콘텐츠 구조적 대칭성을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.content_symmetry_analyzer_service import analyze_content_symmetry
        result = analyze_content_symmetry(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '콘텐츠 대칭성 분석')


# ── Sentence Complexity Scorer ──
@blog_bp.route('/api/score-sentence-complexity', methods=['POST'])
def score_sentence_complexity_route():
    """문장 복잡도를 평가합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import score_sentence_complexity
        result = score_sentence_complexity(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문장 복잡도 평가')


# ── Sentence Starter Diversity ──
@blog_bp.route('/api/analyze-sentence-starter-diversity', methods=['POST'])
def analyze_sentence_starter_diversity_route():
    """문장 시작어 다양성을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import analyze_sentence_starter_diversity
        result = analyze_sentence_starter_diversity(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문장 시작어 다양성 분석')


# ── Average Paragraph Length ──
@blog_bp.route('/api/analyze-avg-paragraph-length', methods=['POST'])
def analyze_avg_paragraph_length_route():
    """단락 평균 길이를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.avg_paragraph_length_service import analyze_avg_paragraph_length
        result = analyze_avg_paragraph_length(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '단락 평균 길이 분석')


@blog_bp.route('/api/analyze-noun-verb-ratio', methods=['POST'])
def analyze_noun_verb_ratio_route():
    """명사/동사 비율을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.noun_verb_ratio_service import analyze_noun_verb_ratio
        result = analyze_noun_verb_ratio(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '명사/동사 비율 분석')


@blog_bp.route('/api/analyze-passive-active-trend', methods=['POST'])
def analyze_passive_active_trend_route():
    """섹션별 능동/피동 비율 추이를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.passive_active_trend_service import analyze_passive_active_trend
        result = analyze_passive_active_trend(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '능동/피동 추이 분석')


# ── List Parallelism Checker ──
@blog_bp.route('/api/check-list-parallelism', methods=['POST'])
def check_list_parallelism_route():
    """목록 항목의 병렬 구조 일관성을 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.list_parallelism_service import check_list_parallelism
        result = check_list_parallelism(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '목록 병렬 구조 검사')


# ── Heading Hierarchy Integrity Checker ──
@blog_bp.route('/api/check-heading-hierarchy', methods=['POST'])
def check_heading_hierarchy_route():
    """마크다운 제목 계층 구조를 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.heading_hierarchy_service import check_heading_hierarchy
        result = check_heading_hierarchy(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '제목 계층 구조 검사')


# ── Numeric & Unit Consistency Checker ──
@blog_bp.route('/api/check-numeric-unit-consistency', methods=['POST'])
def check_numeric_unit_consistency_route():
    """숫자/단위 표기 일관성을 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.numeric_unit_consistency_service import check_numeric_unit_consistency
        result = check_numeric_unit_consistency(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '숫자/단위 일관성 검사')


# ── Topic Sentence Alignment Analyzer ──
@blog_bp.route('/api/analyze-topic-sentence-alignment', methods=['POST'])
def analyze_topic_sentence_alignment_route():
    """문단별 주제문 정렬을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.sentence_analysis_service import analyze_topic_sentence_alignment
        result = analyze_topic_sentence_alignment(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '주제문 정렬 분석')


# ── Paragraph Unity Checker ──
@blog_bp.route('/api/check-paragraph-unity', methods=['POST'])
def check_paragraph_unity_route():
    """문단별 주제 통일성을 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.paragraph_unity_service import check_paragraph_unity
        result = check_paragraph_unity(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문단 통일성 검사')


# ── Adjacent Paragraph Cohesion Analyzer ──
@blog_bp.route('/api/analyze-adjacent-cohesion', methods=['POST'])
def analyze_adjacent_cohesion_route():
    """인접 문단 간 응집도를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.adjacent_cohesion_service import analyze_adjacent_cohesion
        result = analyze_adjacent_cohesion(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문단 응집도 분석')
