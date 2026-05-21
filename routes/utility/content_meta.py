"""콘텐츠 메타데이터 (페르소나/브랜드/투명성/위험) 라우트 — utility_routes.py에서 분리."""
from flask import jsonify, request

from routes.blog_routes import blog_bp
from services.data.supabase_service import require_auth
from utils.responses import handle_error


# ── 약어 추출 ─────────────────────────────────────────

@blog_bp.route('/api/extract-acronyms', methods=['POST'])
def extract_acronyms_route():
    """콘텐츠에서 약어와 전문용어를 추출합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.acronym_extractor_service import extract_acronyms
        result = extract_acronyms(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '약어 추출')


# ── 브랜드 보이스 프로파일링 ──────────────────────────

@blog_bp.route('/api/brand-voice', methods=['POST'])
def brand_voice_route():
    """콘텐츠의 브랜드 보이스(톤, 문체)를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.content.brand_voice_profiler_service import profile_brand_voice
        result = profile_brand_voice(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '브랜드 보이스 분석')


# ── 타겟 독자 페르소나 추론 ──────────────────────────

@blog_bp.route('/api/audience-persona', methods=['POST'])
def audience_persona_route():
    """콘텐츠에서 타겟 독자 페르소나를 추론합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.content.audience_persona_service import build_persona
        result = build_persona(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '독자 페르소나 추론')


# ── 시각 콘텐츠 제안 ─────────────────────────────────

@blog_bp.route('/api/suggest-visuals', methods=['POST'])
def suggest_visuals_route():
    """콘텐츠에 삽입할 시각 콘텐츠를 제안합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.media.visual_content_service import suggest_visuals
        result = suggest_visuals(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '시각 콘텐츠 제안')


# ── 정보 이득 분석 ──────────────────────────────

@blog_bp.route('/api/information-gain', methods=['POST'])
def information_gain_route():
    """콘텐츠의 정보 이득(차별화 수준)을 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        reference_contents = data.get('reference_contents', None)

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.information_gain_service import analyze_information_gain
        result = analyze_information_gain(content, reference_contents)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '정보 이득 분석')


# ── 자막 아티팩트 감지 ──────────────────────────────

@blog_bp.route('/api/detect-artifacts', methods=['POST'])
def detect_artifacts_route():
    """유튜브 자막 전사의 아티팩트를 감지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.transcript.transcript_artifact_service import detect_transcript_artifacts
        result = detect_transcript_artifacts(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '자막 아티팩트 감지')


@blog_bp.route('/api/validate-instruction-sequence', methods=['POST'])
def validate_instruction_sequence_route():
    """절차 시퀀스 검증 API."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.instruction_sequence_service import validate_instruction_sequence
        result = validate_instruction_sequence(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '절차 시퀀스 검증')


# ── Word Frequency Cloud Generator ──
@blog_bp.route('/api/generate-word-frequency', methods=['POST'])
def generate_word_frequency_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.media.word_frequency_cloud_service import generate_word_frequency
        top_n = data.get('top_n', 30)
        result = generate_word_frequency(content, top_n=top_n)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '단어 빈도 분석')


# ── Emotional Arc Mapper ──
@blog_bp.route('/api/map-emotional-arc', methods=['POST'])
def map_emotional_arc_route():
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.emotional_arc_mapper_service import map_emotional_arc
        result = map_emotional_arc(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '감정 아크 매핑')


@blog_bp.route('/api/check-material-connection-disclosure', methods=['POST'])
def check_material_connection_disclosure_route():
    """제휴/협찬 공시 누락을 점검합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.material_connection_disclosure_service import check_material_connection_disclosure
        result = check_material_connection_disclosure(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '이해관계 공시 점검')


@blog_bp.route('/api/check-ai-disclosure', methods=['POST'])
def check_ai_disclosure_route():
    """AI 작성/보조 표시 누락을 점검합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.ai_disclosure_checker_service import check_ai_disclosure
        result = check_ai_disclosure(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, 'AI 공시 점검')


@blog_bp.route('/api/analyze-tradeoff-coverage', methods=['POST'])
def analyze_tradeoff_coverage_route():
    """장단점 균형을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.tradeoff_coverage_analyzer_service import analyze_tradeoff_coverage
        result = analyze_tradeoff_coverage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '장단점 균형 분석')


@blog_bp.route('/api/check-primary-source-preference', methods=['POST'])
def check_primary_source_preference_route():
    """인용 출처의 1차/2차 비율을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.primary_source_preference_service import check_primary_source_preference
        result = check_primary_source_preference(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '출처 품질 분석')


@blog_bp.route('/api/detect-high-stakes-advice-risk', methods=['POST'])
def detect_high_stakes_advice_risk_route():
    """고위험 조언 콘텐츠의 안전성을 점검합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.high_stakes_advice_risk_service import detect_high_stakes_advice_risk
        result = detect_high_stakes_advice_risk(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, 'YMYL 위험 감지')


@blog_bp.route('/api/check-evaluation-criteria-disclosure', methods=['POST'])
def check_evaluation_criteria_disclosure_route():
    """리뷰/비교 글의 평가 기준 공시를 점검합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.evaluation_criteria_disclosure_service import check_evaluation_criteria_disclosure
        result = check_evaluation_criteria_disclosure(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '평가 기준 공시 점검')


@blog_bp.route('/api/analyze-recommendation-justification', methods=['POST'])
def analyze_recommendation_justification_route():
    """추천 항목의 근거 충분성을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.recommendation_justification_service import analyze_recommendation_justification
        result = analyze_recommendation_justification(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '추천 근거 분석')


@blog_bp.route('/api/check-prerequisite-disclosure', methods=['POST'])
def check_prerequisite_disclosure_route():
    """튜토리얼/가이드의 사전조건 공시를 점검합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.prerequisite_disclosure_service import check_prerequisite_disclosure
        result = check_prerequisite_disclosure(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '사전조건 공시 점검')


@blog_bp.route('/api/analyze-troubleshooting-coverage', methods=['POST'])
def analyze_troubleshooting_coverage_route():
    """가이드의 문제 해결 커버리지를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.troubleshooting_coverage_service import analyze_troubleshooting_coverage
        result = analyze_troubleshooting_coverage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '문제 해결 커버리지 분석')


@blog_bp.route('/api/analyze-extractability', methods=['POST'])
def analyze_extractability_route():
    """콘텐츠의 문맥 독립 추출 가능성을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.extractability_analyzer_service import analyze_extractability
        result = analyze_extractability(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '추출 가능성 분석')


@blog_bp.route('/api/analyze-community-evidence', methods=['POST'])
def analyze_community_evidence_route():
    """커뮤니티 근거 포함 여부를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.community_evidence_service import analyze_community_evidence
        result = analyze_community_evidence(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '커뮤니티 근거 분석')


@blog_bp.route('/api/check-update-delta-summary', methods=['POST'])
def check_update_delta_summary_route():
    """업데이트 변경 요약 블록 존재 여부를 점검합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.content.update_delta_summary_service import check_update_delta_summary
        result = check_update_delta_summary(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '업데이트 요약 점검')


# ── Audience-Fit Framing Analyzer ──
@blog_bp.route('/api/analyze-audience-fit-framing', methods=['POST'])
def analyze_audience_fit_framing_route():
    """대상 독자/상황/비적합 프레이밍을 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.quality.audience_fit_framing_service import analyze_audience_fit_framing
        result = analyze_audience_fit_framing(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '대상 프레이밍 분석')


# ── Geo Scope Assumption Detector ──
@blog_bp.route('/api/detect-geo-scope-assumptions', methods=['POST'])
def detect_geo_scope_assumptions_route():
    """지역 의존 정보의 범위 라벨 누락을 탐지합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.geo_scope_assumption_service import detect_geo_scope_assumptions
        result = detect_geo_scope_assumptions(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '지역 범위 가정 탐지')


# ── Absolute Claim Risk Detector ──
@blog_bp.route('/api/detect-absolute-claim-risk', methods=['POST'])
def detect_absolute_claim_risk_route():
    """절대 표현의 위험도를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.absolute_claim_risk_service import detect_absolute_claim_risk
        result = detect_absolute_claim_risk(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '절대 표현 위험 분석')


# ── Step Verification Coverage Analyzer ──
@blog_bp.route('/api/analyze-step-verification-coverage', methods=['POST'])
def analyze_step_verification_coverage_route():
    """가이드 문서의 단계별 검증 기준 커버리지를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.step_verification_coverage_service import analyze_step_verification_coverage
        result = analyze_step_verification_coverage(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '단계 검증 커버리지 분석')


# ── Comparison Criteria Completeness Checker ──
@blog_bp.route('/api/check-comparison-criteria-completeness', methods=['POST'])
def check_comparison_criteria_completeness_route():
    """비교 콘텐츠의 기준 명시 완전성을 검사합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.comparison_criteria_completeness_service import check_comparison_criteria_completeness
        result = check_comparison_criteria_completeness(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '비교 기준 완전성 검사')


# ── Original Evidence Signal Analyzer ──
@blog_bp.route('/api/analyze-original-evidence', methods=['POST'])
def analyze_original_evidence_route():
    """원본 증거 신호를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.original_evidence_signal_service import analyze_original_evidence
        result = analyze_original_evidence(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '원본 증거 신호 분석')


# ── Claim-Evidence Distance Analyzer ──
@blog_bp.route('/api/analyze-claim-evidence-distance', methods=['POST'])
def analyze_claim_evidence_distance_route():
    """주장-근거 거리를 분석합니다."""
    try:
        data = request.get_json(force=True)
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.claim_evidence_distance_service import analyze_claim_evidence_distance
        result = analyze_claim_evidence_distance(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '주장-근거 거리 분석')


# ── Definition Gap Detector ──
@blog_bp.route('/api/detect-definition-gaps', methods=['POST'])
def detect_definition_gaps_route():
    """정의 없는 전문 용어/약어를 탐지합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.definition_gap_service import detect_definition_gaps
        result = detect_definition_gaps(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '정의 갭 탐지')


# ── Methodology Transparency Checker ──
@blog_bp.route('/api/check-methodology-transparency', methods=['POST'])
def check_methodology_transparency_route():
    """방법론 투명성을 검사합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        if not content or not content.strip():
            return jsonify({'error': '분석할 콘텐츠가 필요합니다.'}), 400

        from services.analysis.methodology_transparency_service import check_methodology_transparency
        result = check_methodology_transparency(content)
        return jsonify(result)

    except Exception as e:
        return handle_error(e, '방법론 투명성 검사')


@blog_bp.route('/api/scheduler/status', methods=['GET'])
@require_auth
def scheduler_status():
    """스케줄러 실행 상태 및 등록된 잡 목록을 조회합니다."""
    from services.data.scheduler_worker import scheduler

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger),
        })

    return jsonify({
        'running': scheduler.running,
        'jobs': jobs,
        'total_jobs': len(jobs),
    })
