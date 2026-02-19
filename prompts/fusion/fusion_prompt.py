"""퓨전 통합 프롬프트 — 여러 소스를 융합하여 최종 글 생성"""

FUSION_PROMPT = '''
# 역할: 다중 소스 융합 에디터

당신은 여러 YouTube 영상, 시청자 댓글, 외부 기사의 정보를 융합하여
하나의 완벽한 글을 작성하는 전문 에디터입니다.

## 핵심 원칙

1. **중복 제거, 고유 관점 보존**: 영상마다 겹치는 내용은 한 번만, 각 영상만의 고유한 인사이트는 반드시 포함
2. **댓글 인사이트 녹여내기**: "시청자들의 실제 경험에 따르면...", "댓글에서 자주 언급된 바와 같이..." 형태로 본문 중간에 자연스럽게 반영
3. **팩트체크 인라인 표시**: 댓글에서 지적된 오류는 본문 해당 위치에 "> ⚠️ **팩트체크**: ..." 형태로 표시
4. **FAQ 섹션**: 댓글의 질문들을 정리하여 글 말미에 "## 자주 묻는 질문" 섹션으로 구성 (Q&A 형식)
5. **출처 표시**: 외부 소스 정보 사용 시 "[출처: 기사제목]" 형태로 인라인 표시
6. **참고 소스 목록**: 글 맨 끝에 "## 참고 소스" 섹션으로 모든 소스 나열

## 금지 사항
- 소스에 없는 정보 창작/추측 절대 금지
- 금지 표현: 놀라운, 혁신적, 획기적, 최고의, 게임체인저, 압도적, 경이로운, 드디어, 탁월한, 인상적, 뛰어난, 강력한
- 댓글 섹션이 입력에 없으면 시청자 반응 절대 언급 금지

## 출력 형식
- 마크다운
- 제목은 # 하나만
- 본문 → FAQ(있으면) → 참고 소스 순서
'''


def build_fusion_context(video_summaries, comment_analysis=None, web_sources=None):
    """Phase 1~2 결과를 Phase 3 입력용 컨텍스트 문자열로 조합

    Args:
        video_summaries: [{'title': str, 'summary': str}, ...]
        comment_analysis: {'insights': [...], 'questions': [...],
                           'fact_checks': [...], 'sentiments': [...]} 또는 None
        web_sources: [{'title': str, 'summary': str, 'url': str}, ...] 또는 None

    Returns:
        str: 통합 컨텍스트 문자열
    """
    parts = []

    # 영상 요약
    parts.append('[영상 요약]')
    for i, v in enumerate(video_summaries, 1):
        parts.append(f'\n### 영상 {i}: {v["title"]}\n{v["summary"]}')

    # 댓글 분석
    if comment_analysis:
        parts.append('\n\n[댓글 분석]')
        if comment_analysis.get('insights'):
            parts.append('\n#### 인사이트 (본문에 녹여내기)')
            for item in comment_analysis['insights']:
                parts.append(f'- {item}')
        if comment_analysis.get('questions'):
            parts.append('\n#### 질문 (FAQ 섹션용)')
            for item in comment_analysis['questions']:
                parts.append(f'- {item}')
        if comment_analysis.get('fact_checks'):
            parts.append('\n#### 팩트체크 (인라인 표시)')
            for item in comment_analysis['fact_checks']:
                parts.append(f'- {item}')
        if comment_analysis.get('sentiments'):
            parts.append('\n#### 감상')
            for item in comment_analysis['sentiments']:
                parts.append(f'- {item}')

    # 외부 소스
    if web_sources:
        parts.append('\n\n[외부 소스]')
        for ws in web_sources:
            parts.append(f'\n#### {ws["title"]} ({ws["url"]})\n{ws["summary"]}')

    return '\n'.join(parts)
