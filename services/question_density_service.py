"""
Question Density Analyzer 서비스

콘텐츠에서 질문의 빈도와 분포를 분석하여
독자 참여도와 대화형 글쓰기 품질을 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


# 마크다운 헤딩
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# 한국어 질문 패턴
_QUESTION_PATTERNS_KO = [
    re.compile(r'[가-힣].+\?'),                    # 한글 + ?
    re.compile(r'(?:할까요|인가요|일까요|인지|인가)\s*[.?]?'),
    re.compile(r'(?:무엇|어떤|어떻게|왜|어디|언제|누가|얼마)\s'),
    re.compile(r'(?:아닌가|않을까|될까|할까)\s'),
]

# 영어 질문 패턴
_QUESTION_PATTERNS_EN = [
    re.compile(r'[A-Za-z].+\?'),                   # 영문 + ?
    re.compile(r'^(?:What|Why|How|When|Where|Who|Which|Do|Does|Did|Is|Are|Was|Were|Can|Could|Should|Would|Will)\s', re.IGNORECASE | re.MULTILINE),
]

# 수사적 질문 패턴 (자문자답)
_RHETORICAL_PATTERNS = [
    re.compile(r'\?\s*(?:네|예|아닙니다|그렇습니다|물론|당연히|바로)'),
    re.compile(r'\?\s*(?:Yes|No|Of course|Absolutely|Exactly)\b', re.IGNORECASE),
]

# 문장 분리
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')


def _split_sentences(text: str) -> List[str]:
    cleaned = _HEADING_RE.sub('', text)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 3]


def _is_question(sentence: str) -> bool:
    for p in _QUESTION_PATTERNS_KO + _QUESTION_PATTERNS_EN:
        if p.search(sentence):
            return True
    return False


def _is_rhetorical(sentence: str, next_sentence: str = '') -> bool:
    combined = sentence + ' ' + next_sentence
    for p in _RHETORICAL_PATTERNS:
        if p.search(combined):
            return True
    return False


def _parse_sections(content: str) -> List[Dict]:
    lines = content.split('\n')
    sections = []
    current = {'section': '(서론)', 'lines': []}
    for line in lines:
        m = _HEADING_RE.match(line.strip())
        if m:
            if current['lines'] or current['section'] != '(서론)':
                sections.append(current)
            current = {'section': m.group(2).strip(), 'lines': []}
        else:
            current['lines'].append(line)
    sections.append(current)
    if sections and sections[0]['section'] == '(서론)' and not ''.join(sections[0]['lines']).strip():
        sections = sections[1:]
    return sections


def analyze_question_density(content: str) -> dict:
    """콘텐츠의 질문 밀도를 분석합니다.

    Returns:
        questions, section_analysis, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'questions': [],
            'section_analysis': [],
            'summary': {'total_questions': 0, 'total_sentences': 0,
                        'question_density': 0.0, 'rhetorical_count': 0},
            'score': 50.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    sentences = _split_sentences(content)
    if not sentences:
        return {
            'questions': [],
            'section_analysis': [],
            'summary': {'total_questions': 0, 'total_sentences': 0,
                        'question_density': 0.0, 'rhetorical_count': 0},
            'score': 50.0,
            'suggestions': [],
        }

    # 질문 감지
    questions = []
    rhetorical_count = 0
    for i, sent in enumerate(sentences):
        if _is_question(sent):
            next_s = sentences[i + 1] if i + 1 < len(sentences) else ''
            is_rhet = _is_rhetorical(sent, next_s)
            if is_rhet:
                rhetorical_count += 1
            questions.append({
                'text': sent if len(sent) <= 100 else sent[:97] + '...',
                'is_rhetorical': is_rhet,
                'position_index': i,
            })

    total_q = len(questions)
    total_s = len(sentences)
    density = round((total_q / total_s * 100) if total_s > 0 else 0.0, 1)

    # 섹션별 분석
    sections = _parse_sections(content)
    section_analysis = []
    for sec in sections:
        text = '\n'.join(sec['lines'])
        sec_sents = _split_sentences(text)
        sec_questions = sum(1 for s in sec_sents if _is_question(s))
        section_analysis.append({
            'section': sec['section'],
            'questions': sec_questions,
            'sentences': len(sec_sents),
        })

    # 점수: 적정 밀도 5-15%
    if density == 0:
        score = 40.0
    elif density < 3:
        score = 50.0 + density * 5
    elif density <= 15:
        score = 80.0 + min(20.0, (density - 3) * (20.0 / 12.0))
    elif density <= 25:
        score = 100.0 - (density - 15) * 3
    else:
        score = max(0.0, 70.0 - (density - 25) * 2)
    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(total_q, density, rhetorical_count, sections)

    return {
        'questions': questions,
        'section_analysis': section_analysis,
        'summary': {
            'total_questions': total_q,
            'total_sentences': total_s,
            'question_density': density,
            'rhetorical_count': rhetorical_count,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(total: int, density: float, rhetorical: int, sections: list) -> List[str]:
    suggestions = []
    if total == 0:
        suggestions.append('질문이 없습니다. 독자의 호기심을 유발하는 질문을 추가하면 참여도가 높아집니다.')
        return suggestions
    if density > 25:
        suggestions.append(f'질문 밀도 {density}%로 과다합니다 (적정: 5-15%). 일부를 서술문으로 바꾸세요.')
    elif density < 3:
        suggestions.append(f'질문 밀도 {density}%로 낮습니다. 독자 참여를 위해 질문을 추가하세요.')
    else:
        suggestions.append(f'질문 밀도 {density}%로 적정합니다.')
    if rhetorical > 0:
        suggestions.append(f'수사적 질문 {rhetorical}개: 자문자답 패턴이 과하면 독자가 피로감을 느낍니다.')
    return suggestions
