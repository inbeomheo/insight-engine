"""표현 품질 (군더더기/어휘/톤/클리셰) 라우트 — utility_routes.py에서 분리."""
from flask import jsonify, request

from routes.blog_routes import blog_bp
from services.data.supabase_service import require_auth
from utils.responses import handle_error


# ── 파워워드 분석 ─────────────────────────────────────

@blog_bp.route('/api/power-words', methods=['POST'])
def power_words_route():
    """콘텐츠의 파워워드를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        goal = data.get('goal', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.power_word_service import analyze_power_words, suggest_power_words
        result = analyze_power_words(content)
        if goal:
            result['recommended'] = suggest_power_words(content, goal)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '파워워드 분석')


# ── 감정 톤 매핑 ─────────────────────────────────────

@blog_bp.route('/api/emotional-tone', methods=['POST'])
def emotional_tone_route():
    """콘텐츠의 감정 흐름을 매핑합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.emotional_tone_service import map_emotional_tone
        result = map_emotional_tone(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '감정 톤 매핑')


# ── 참여 점수 ─────────────────────────────────────────

@blog_bp.route('/api/engagement-score', methods=['POST'])
def engagement_score_route():
    """콘텐츠의 참여 유도력을 종합 평가합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.seo.engagement_scorer_service import score_engagement
        result = score_engagement(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '참여 점수 분석')


# ── 중복 표현 검사 ────────────────────────────────────

@blog_bp.route('/api/check-redundancy', methods=['POST'])
def check_redundancy_route():
    """콘텐츠의 중복/반복 표현을 감지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.redundancy_checker_service import check_redundancy
        result = check_redundancy(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '중복 표현 검사')


# ── 피동 표현 감지 ────────────────────────────────────

@blog_bp.route('/api/detect-passive', methods=['POST'])
def detect_passive_route():
    """한국어 피동 표현을 감지하고 능동 전환을 제안합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.passive_voice_service import detect_passive
        result = detect_passive(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '피동 표현 감지')


# ── 군더더기/헤지 표현 감지 ──────────────────────────────

@blog_bp.route('/api/detect-fillers', methods=['POST'])
def detect_fillers_route():
    """콘텐츠의 군더더기 및 헤지 표현을 감지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.filler_detector_service import detect_fillers
        result = detect_fillers(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '군더더기 표현 감지')


# ── 포용적 언어 검사 ──────────────────────────────

@blog_bp.route('/api/check-inclusive-language', methods=['POST'])
def check_inclusive_language_route():
    """콘텐츠의 포용적 언어 사용을 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.inclusive_language_service import check_inclusive_language
        result = check_inclusive_language(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '포용적 언어 검사')


# ── 홍보 톤 포화도 검사 ──────────────────────────────

@blog_bp.route('/api/check-promotional-tone', methods=['POST'])
def check_promotional_tone_route():
    """콘텐츠의 홍보/세일즈 표현 밀도를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.promotional_tone_service import check_promotional_tone
        result = check_promotional_tone(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '홍보 톤 분석')


# ── 수치 약속 무결성 검사 ──────────────────────────────

@blog_bp.route('/api/check-numerical-promises', methods=['POST'])
def check_numerical_promises_route():
    """제목의 수치 약속이 본문에서 이행되는지 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.numerical_promise_service import check_numerical_promises
        result = check_numerical_promises(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '수치 약속 검사')


# ── 전문 용어 정의 커버리지 ──────────────────────────────

@blog_bp.route('/api/analyze-jargon', methods=['POST'])
def analyze_jargon_route():
    """전문 용어/약어의 정의 동반 여부를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.jargon_analyzer_service import analyze_jargon_coverage
        result = analyze_jargon_coverage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '전문 용어 분석')


# ── 음성 적합성 분석 ──────────────────────────────

@blog_bp.route('/api/analyze-speakability', methods=['POST'])
def analyze_speakability_route():
    """콘텐츠의 음성 재생 적합성을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.speakability_service import analyze_speakability
        result = analyze_speakability(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '음성 적합성 분석')


# ── 섹션 주제 이탈 감지 ──────────────────────────────

@blog_bp.route('/api/detect-section-drift', methods=['POST'])
def detect_section_drift_route():
    """각 섹션이 소제목 주제에서 벗어나는 지점을 감지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.section_drift_service import detect_section_drift
        result = detect_section_drift(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '섹션 이탈 감지')


# ── Adverb Overuse Detector ──────────────────────────────────────────
@blog_bp.route('/api/detect-adverb-overuse', methods=['POST'])
def detect_adverb_overuse_route():
    """부사 남용을 감지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.adverb_overuse_service import detect_adverb_overuse
        result = detect_adverb_overuse(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '부사 남용 감지')


# ── Statistics Coverage Analyzer ─────────────────────────────────────
@blog_bp.route('/api/analyze-statistics-coverage', methods=['POST'])
def analyze_statistics_coverage_route():
    """섹션별 수치 근거 커버리지를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.statistics_coverage_service import analyze_statistics_coverage
        result = analyze_statistics_coverage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '수치 커버리지 분석')


# ── Simple Alternative Finder ────────────────────────────────────────
@blog_bp.route('/api/find-simple-alternatives', methods=['POST'])
def find_simple_alternatives_route():
    """고난도 어휘의 쉬운 대체어를 제안합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.simple_alternative_service import find_simple_alternatives
        result = find_simple_alternatives(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '쉬운 대체어 검색')


@blog_bp.route('/api/check-thesis-frontload', methods=['POST'])
def check_thesis_frontload_route():
    """핵심 주장 프론트로드 점검 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.thesis_frontload_service import check_thesis_frontload
        result = check_thesis_frontload(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '핵심 주장 프론트로드 점검')


@blog_bp.route('/api/audit-whitespace-formatting', methods=['POST'])
def audit_whitespace_formatting_route():
    """공백/포맷 점검 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.whitespace_formatting_service import audit_whitespace_formatting
        result = audit_whitespace_formatting(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '공백/포맷 점검')


@blog_bp.route('/api/analyze-bullet-density', methods=['POST'])
def analyze_bullet_density_route():
    """불릿 리스트 밀도 분석 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.bullet_point_density_service import analyze_bullet_density
        result = analyze_bullet_density(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '불릿 리스트 밀도 분석')


@blog_bp.route('/api/check-code-block-quality', methods=['POST'])
def check_code_block_quality_route():
    """코드 블록 품질 점검 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.code_block_quality_service import check_code_block_quality
        result = check_code_block_quality(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '코드 블록 품질 점검')


# ── Parenthetical Overuse Checker ──
@blog_bp.route('/api/check-parenthetical-overuse', methods=['POST'])
def check_parenthetical_overuse_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.parenthetical_overuse_service import check_parenthetical_overuse
        result = check_parenthetical_overuse(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '괄호 과다 사용 검사')


# ── Anaphora Repetition Detector ──
@blog_bp.route('/api/detect-anaphora-repetition', methods=['POST'])
def detect_anaphora_repetition_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.anaphora_repetition_service import detect_anaphora_repetition
        result = detect_anaphora_repetition(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '수사 반복 감지')


# ── Emoji Usage Analyzer ──
@blog_bp.route('/api/analyze-emoji-usage', methods=['POST'])
def analyze_emoji_usage_route():
    """이모지 사용 패턴을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.emoji_usage_analyzer_service import analyze_emoji_usage
        result = analyze_emoji_usage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '이모지 사용 분석')


# ── Rhetorical Device Detector ──
@blog_bp.route('/api/detect-rhetorical-devices', methods=['POST'])
def detect_rhetorical_devices_route():
    """수사법을 감지합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.rhetorical_device_detector_service import detect_rhetorical_devices
        result = detect_rhetorical_devices(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '수사법 감지')


# ── Cliché Detector ──
@blog_bp.route('/api/detect-cliches', methods=['POST'])
def detect_cliches_route():
    """진부한 표현을 감지합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.cliche_detector_service import detect_cliches
        result = detect_cliches(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '클리셰 감지')


# ── Gender-Neutral Language Checker ──
@blog_bp.route('/api/check-gender-neutral', methods=['POST'])
def check_gender_neutral_route():
    """성별 포용적 언어 사용을 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.gender_neutral_language_service import check_gender_neutral
        result = check_gender_neutral(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '성별 포용 언어 검사')


# ── Temporal Reference Checker ──
@blog_bp.route('/api/check-temporal-references', methods=['POST'])
def check_temporal_references_route():
    """시제/시간 참조 일관성을 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.temporal_reference_checker_service import check_temporal_references
        result = check_temporal_references(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '시제 참조 검사')


# ── Quotation Usage Analyzer ──
@blog_bp.route('/api/analyze-quotation-usage', methods=['POST'])
def analyze_quotation_usage_route():
    """인용문 사용 패턴을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.quotation_usage_analyzer_service import analyze_quotation_usage
        result = analyze_quotation_usage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '인용문 사용 분석')


# ── Quantifier Specificity Analyzer ──
@blog_bp.route('/api/analyze-quantifier-specificity', methods=['POST'])
def analyze_quantifier_specificity_route():
    """수량 표현의 구체성을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.quantifier_specificity_service import analyze_quantifier_specificity
        result = analyze_quantifier_specificity(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '수량 구체성 분석')


# ── Terminology Drift Analyzer ──
@blog_bp.route('/api/analyze-terminology-drift', methods=['POST'])
def analyze_terminology_drift_route():
    """섹션 간 용어 혼용을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.terminology_drift_service import analyze_terminology_drift
        result = analyze_terminology_drift(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '용어 혼용 분석')


# ── Concept Load Analyzer ──
@blog_bp.route('/api/analyze-concept-load', methods=['POST'])
def analyze_concept_load_route():
    """구간별 인지부하를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.concept_load_service import analyze_concept_load
        result = analyze_concept_load(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '인지부하 분석')


# ── 스케줄러 상태 조회 ──────────────────────────────────────
