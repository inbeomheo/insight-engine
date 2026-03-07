"""
Schema Opportunity Finder 서비스

콘텐츠를 분석하여 구조화 데이터(JSON-LD) 적용 기회를 찾습니다.
7가지 스키마 타입(FAQPage, HowTo, Article, VideoObject, Clip,
DefinedTerm, ItemList)을 규칙 기반으로 감지합니다.
"""
import re
import json
import logging

logger = logging.getLogger(__name__)

# ── 스키마 타입별 감지 패턴 ──

_FAQ_PATTERNS = [
    re.compile(r'.{2,}인가요\??'),
    re.compile(r'.{2,}할까요\??'),
    re.compile(r'.{2,}일까요\??'),
    re.compile(r'.{2,}나요\??'),
    re.compile(r'^Q\s*[:：.]', re.MULTILINE),
    re.compile(r'질문\s*[:：]', re.MULTILINE),
    re.compile(r'\?\s*$', re.MULTILINE),
]

_HOWTO_PATTERNS = [
    re.compile(r'\d+\s*단계'),
    re.compile(r'[Ss]tep\s*\d+', re.IGNORECASE),
    re.compile(r'먼저.{2,}다음.{2,}마지막으로', re.DOTALL),
    re.compile(r'먼저'),
    re.compile(r'다음으로'),
    re.compile(r'마지막으로'),
    re.compile(r'준비물'),
    re.compile(r'순서대로'),
    re.compile(r'절차'),
]

_VIDEO_PATTERNS = [
    re.compile(r'\[\d{1,2}:\d{2}\]'),
    re.compile(r'\d{1,2}:\d{2}'),
    re.compile(r'영상'),
    re.compile(r'동영상'),
    re.compile(r'비디오'),
    re.compile(r'[Vv]ideo'),
    re.compile(r'[Yy]ou[Tt]ube'),
]

_CLIP_PATTERNS = [
    re.compile(r'\[\d{1,2}:\d{2}\]'),
    re.compile(r'\d{1,2}:\d{2}\s*[-~]\s*\d{1,2}:\d{2}'),
    re.compile(r'\d{1,2}:\d{2}'),
]

_DEFINED_TERM_PATTERNS = [
    re.compile(r'.{2,}이란\s'),
    re.compile(r'.{2,}란\s'),
    re.compile(r'.{2,}는\s.{2,}를?\s*말한다'),
    re.compile(r'.{2,}는\s.{2,}을?\s*의미한다'),
    re.compile(r'정의\s*[:：]'),
    re.compile(r'개념\s*[:：]'),
    re.compile(r'.{2,}는\s.{2,}이다'),
]

_ITEMLIST_PATTERNS = [
    re.compile(r'[Tt]op\s*\d+', re.IGNORECASE),
    re.compile(r'\d+\s*가지'),
    re.compile(r'\d+\s*선'),
    re.compile(r'^\s*\d+[\.\)]\s+', re.MULTILINE),
    re.compile(r'^\s*[-•]\s+', re.MULTILINE),
    re.compile(r'베스트\s*\d+'),
    re.compile(r'추천\s*\d+'),
]

# ── JSON-LD 템플릿 ──

_TEMPLATES = {
    'FAQPage': json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{
            "@type": "Question",
            "name": "",
            "acceptedAnswer": {"@type": "Answer", "text": ""}
        }]
    }, ensure_ascii=False, indent=2),

    'HowTo': json.dumps({
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": "",
        "step": [{
            "@type": "HowToStep",
            "name": "",
            "text": ""
        }]
    }, ensure_ascii=False, indent=2),

    'Article': json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "",
        "author": {"@type": "Person", "name": ""},
        "datePublished": "",
        "description": ""
    }, ensure_ascii=False, indent=2),

    'VideoObject': json.dumps({
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": "",
        "description": "",
        "thumbnailUrl": "",
        "uploadDate": "",
        "contentUrl": ""
    }, ensure_ascii=False, indent=2),

    'Clip': json.dumps({
        "@context": "https://schema.org",
        "@type": "Clip",
        "name": "",
        "startOffset": 0,
        "endOffset": 0,
        "url": ""
    }, ensure_ascii=False, indent=2),

    'DefinedTerm': json.dumps({
        "@context": "https://schema.org",
        "@type": "DefinedTerm",
        "name": "",
        "description": "",
        "inDefinedTermSet": ""
    }, ensure_ascii=False, indent=2),

    'ItemList': json.dumps({
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "",
        "itemListElement": [{
            "@type": "ListItem",
            "position": 1,
            "name": ""
        }]
    }, ensure_ascii=False, indent=2),
}

# 총 스키마 타입 수 (커버리지 계산용)
_TOTAL_SCHEMA_TYPES = 7


def find_schema_opportunities(content: str) -> dict:
    """콘텐츠를 분석하여 구조화 데이터 적용 기회를 찾습니다.

    Args:
        content: 분석할 콘텐츠 텍스트

    Returns:
        {
            "opportunities": [{"schema_type", "confidence", "evidence", "json_ld_template", "priority"}],
            "total_opportunities": int,
            "coverage_score": float,
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'opportunities': [],
            'total_opportunities': 0,
            'coverage_score': 0.0,
            'suggestions': ['콘텐츠가 비어 있습니다. 분석할 텍스트를 입력해 주세요.'],
        }

    opportunities = []

    # 각 스키마 타입별 감지
    detectors = [
        ('FAQPage', _detect_faq),
        ('HowTo', _detect_howto),
        ('Article', _detect_article),
        ('VideoObject', _detect_video_object),
        ('Clip', _detect_clip),
        ('DefinedTerm', _detect_defined_term),
        ('ItemList', _detect_item_list),
    ]

    for schema_type, detector in detectors:
        result = detector(content)
        if result['confidence'] > 0:
            opportunities.append({
                'schema_type': schema_type,
                'confidence': result['confidence'],
                'evidence': result['evidence'],
                'json_ld_template': _TEMPLATES[schema_type],
                'priority': _calc_priority(result['confidence']),
            })

    # 신뢰도 내림차순 정렬
    opportunities.sort(key=lambda x: x['confidence'], reverse=True)

    # 커버리지 점수: 감지된 스키마 수 / 전체 타입 수 * 100
    coverage = (len(opportunities) / _TOTAL_SCHEMA_TYPES) * 100

    suggestions = _generate_suggestions(opportunities, content)

    return {
        'opportunities': opportunities,
        'total_opportunities': len(opportunities),
        'coverage_score': round(coverage, 1),
        'suggestions': suggestions,
    }


# ── 스키마 타입별 감지 함수 ──

def _detect_faq(content: str) -> dict:
    """FAQPage 스키마 감지: 질문형 소제목"""
    evidence = []
    for p in _FAQ_PATTERNS:
        for m in p.finditer(content):
            line = _extract_line(content, m.start())
            if line and line not in evidence:
                evidence.append(line)

    confidence = min(len(evidence) * 20, 100) if evidence else 0
    return {'confidence': confidence, 'evidence': evidence[:5]}


def _detect_howto(content: str) -> dict:
    """HowTo 스키마 감지: 순서형 문장"""
    evidence = []
    for p in _HOWTO_PATTERNS:
        for m in p.finditer(content):
            line = _extract_line(content, m.start())
            if line and line not in evidence:
                evidence.append(line)

    confidence = min(len(evidence) * 15, 100) if evidence else 0
    return {'confidence': confidence, 'evidence': evidence[:5]}


def _detect_article(content: str) -> dict:
    """Article 스키마 감지: 제목+본문 구조"""
    evidence = []

    # 제목 패턴 (마크다운 헤딩, HTML 헤딩)
    headings = re.findall(r'^#{1,3}\s+(.+)$', content, re.MULTILINE)
    if headings:
        evidence.append(f'제목 발견: {headings[0]}')

    # 본문 길이 확인 (최소 100자)
    text_len = len(content.strip())
    if text_len >= 100:
        evidence.append(f'본문 길이: {text_len}자')

    # 단락 구조 확인
    paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) >= 20]
    if len(paragraphs) >= 2:
        evidence.append(f'{len(paragraphs)}개 단락 구조 감지')

    # Article은 기본 스키마 — 본문만 있어도 적용 가능
    if text_len >= 100:
        confidence = 40
        if headings:
            confidence += 25
        if len(paragraphs) >= 2:
            confidence += 20
        if text_len >= 500:
            confidence += 15
        confidence = min(confidence, 100)
    else:
        confidence = 0

    return {'confidence': confidence, 'evidence': evidence[:5]}


def _detect_video_object(content: str) -> dict:
    """VideoObject 스키마 감지: 타임스탬프, 영상 관련 키워드"""
    evidence = []
    for p in _VIDEO_PATTERNS:
        for m in p.finditer(content):
            line = _extract_line(content, m.start())
            if line and line not in evidence:
                evidence.append(line)

    # 타임스탬프가 있으면 가중치 높임
    timestamp_count = len(re.findall(r'\d{1,2}:\d{2}', content))
    confidence = 0
    if evidence:
        confidence = min(len(evidence) * 15 + timestamp_count * 10, 100)

    return {'confidence': confidence, 'evidence': evidence[:5]}


def _detect_clip(content: str) -> dict:
    """Clip 스키마 감지: 타임스탬프 + 구간 설명"""
    evidence = []
    for p in _CLIP_PATTERNS:
        for m in p.finditer(content):
            line = _extract_line(content, m.start())
            if line and line not in evidence:
                evidence.append(line)

    # 구간 범위 패턴이 있으면 가중치 높임
    range_count = len(re.findall(r'\d{1,2}:\d{2}\s*[-~]\s*\d{1,2}:\d{2}', content))
    confidence = 0
    if evidence:
        confidence = min(len(evidence) * 15 + range_count * 20, 100)

    return {'confidence': confidence, 'evidence': evidence[:5]}


def _detect_defined_term(content: str) -> dict:
    """DefinedTerm 스키마 감지: 정의문"""
    evidence = []
    for p in _DEFINED_TERM_PATTERNS:
        for m in p.finditer(content):
            line = _extract_line(content, m.start())
            if line and line not in evidence:
                evidence.append(line)

    confidence = min(len(evidence) * 25, 100) if evidence else 0
    return {'confidence': confidence, 'evidence': evidence[:5]}


def _detect_item_list(content: str) -> dict:
    """ItemList 스키마 감지: 목록형 콘텐츠"""
    evidence = []
    for p in _ITEMLIST_PATTERNS:
        for m in p.finditer(content):
            line = _extract_line(content, m.start())
            if line and line not in evidence:
                evidence.append(line)

    # 번호 매기기 항목 수 확인
    numbered_items = len(re.findall(r'^\s*\d+[\.\)]\s+', content, re.MULTILINE))
    bullet_items = len(re.findall(r'^\s*[-•]\s+', content, re.MULTILINE))
    list_items = numbered_items + bullet_items

    confidence = 0
    if evidence:
        confidence = min(len(evidence) * 12 + list_items * 5, 100)

    return {'confidence': confidence, 'evidence': evidence[:5]}


# ── 헬퍼 함수 ──

def _extract_line(content: str, pos: int) -> str:
    """주어진 위치에서 해당 줄 전체를 추출합니다."""
    start = content.rfind('\n', 0, pos) + 1
    end = content.find('\n', pos)
    if end == -1:
        end = len(content)
    line = content[start:end].strip()
    # 너무 긴 줄은 잘라서 반환
    if len(line) > 100:
        line = line[:97] + '...'
    return line


def _calc_priority(confidence: int) -> str:
    """신뢰도에 따른 우선순위 계산."""
    if confidence >= 70:
        return 'high'
    elif confidence >= 40:
        return 'medium'
    return 'low'


def _generate_suggestions(opportunities: list, content: str) -> list:
    """감지 결과 기반 개선 제안을 생성합니다."""
    suggestions = []
    detected_types = {o['schema_type'] for o in opportunities}

    if not opportunities:
        suggestions.append('구조화 데이터 기회가 감지되지 않았습니다. 콘텐츠에 FAQ, 순서형 설명, 목록 등을 추가해 보세요.')
        return suggestions

    # 미감지 스키마에 대한 제안
    all_types = {'FAQPage', 'HowTo', 'Article', 'VideoObject', 'Clip', 'DefinedTerm', 'ItemList'}
    missing = all_types - detected_types

    type_tips = {
        'FAQPage': '질문-답변 형식의 FAQ 섹션을 추가하면 FAQPage 스키마를 적용할 수 있습니다.',
        'HowTo': '"1단계", "2단계" 등 순서형 설명을 추가하면 HowTo 스키마를 적용할 수 있습니다.',
        'VideoObject': '영상 URL이나 타임스탬프를 포함하면 VideoObject 스키마를 적용할 수 있습니다.',
        'Clip': '타임스탬프 구간(예: 00:00~01:30)을 포함하면 Clip 스키마를 적용할 수 있습니다.',
        'DefinedTerm': '용어 정의("~이란", "~는 ~를 말한다")를 추가하면 DefinedTerm 스키마를 적용할 수 있습니다.',
        'ItemList': '"Top N", "N가지" 등 목록형 콘텐츠를 추가하면 ItemList 스키마를 적용할 수 있습니다.',
    }

    for t in missing:
        if t in type_tips:
            suggestions.append(type_tips[t])

    # 높은 신뢰도 스키마 우선 적용 권장
    high_priority = [o for o in opportunities if o['priority'] == 'high']
    if high_priority:
        types_str = ', '.join(o['schema_type'] for o in high_priority)
        suggestions.append(f'높은 신뢰도로 감지된 {types_str} 스키마를 우선 적용하는 것을 권장합니다.')

    return suggestions
