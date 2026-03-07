"""
약어/전문용어 추출 서비스

콘텐츠에서 약어(acronyms)와 전문용어를 추출하고
설명을 생성하여 독자 이해도를 높입니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

_UPPERCASE_ACRONYM_RE = re.compile(r'(?<![A-Za-z])([A-Z][A-Za-z0-9]{1,5})(?![A-Za-z])')
_CAMEL_TERM_RE = re.compile(r'(?<![A-Za-z])([A-Z][a-z]+[A-Z][A-Za-z]*)(?![A-Za-z])')

# 알려진 약어 사전
_KNOWN_ACRONYMS = {
    'AI': '인공지능 (Artificial Intelligence)',
    'ML': '머신러닝 (Machine Learning)',
    'DL': '딥러닝 (Deep Learning)',
    'NLP': '자연어 처리 (Natural Language Processing)',
    'API': '응용 프로그래밍 인터페이스 (Application Programming Interface)',
    'SDK': '소프트웨어 개발 키트 (Software Development Kit)',
    'UI': '사용자 인터페이스 (User Interface)',
    'UX': '사용자 경험 (User Experience)',
    'SEO': '검색엔진 최적화 (Search Engine Optimization)',
    'SaaS': '서비스형 소프트웨어 (Software as a Service)',
    'REST': '표현 상태 전이 (Representational State Transfer)',
    'JSON': '자바스크립트 객체 표기법 (JavaScript Object Notation)',
    'HTML': '하이퍼텍스트 마크업 언어 (HyperText Markup Language)',
    'CSS': '종속형 스타일 시트 (Cascading Style Sheets)',
    'SQL': '구조화 질의 언어 (Structured Query Language)',
    'DB': '데이터베이스 (Database)',
    'CI': '지속적 통합 (Continuous Integration)',
    'CD': '지속적 배포 (Continuous Deployment)',
    'DevOps': '개발운영 (Development + Operations)',
    'CMS': '콘텐츠 관리 시스템 (Content Management System)',
    'CTA': '행동 유도 (Call to Action)',
    'KPI': '핵심 성과 지표 (Key Performance Indicator)',
    'ROI': '투자 수익률 (Return on Investment)',
    'B2B': '기업 간 거래 (Business to Business)',
    'B2C': '기업-소비자 거래 (Business to Consumer)',
    'MVP': '최소 기능 제품 (Minimum Viable Product)',
    'SEM': '검색엔진 마케팅 (Search Engine Marketing)',
    'CTR': '클릭률 (Click-Through Rate)',
    'CPC': '클릭당 비용 (Cost Per Click)',
    'CPM': '천 회 노출당 비용 (Cost Per Mille)',
    'ROAS': '광고 투자 수익률 (Return On Ad Spend)',
    'LTV': '고객 생애 가치 (Lifetime Value)',
    'CAC': '고객 획득 비용 (Customer Acquisition Cost)',
    'OKR': '목표 및 핵심 결과 (Objectives and Key Results)',
    'PR': '홍보 (Public Relations)',
    'SNS': '소셜 네트워크 서비스 (Social Network Service)',
    'RSS': '풍부한 사이트 요약 (Really Simple Syndication)',
    'URL': '통합 자원 위치 지정자 (Uniform Resource Locator)',
    'PDF': '이동 문서 형식 (Portable Document Format)',
    'GPU': '그래픽 처리 장치 (Graphics Processing Unit)',
    'CPU': '중앙 처리 장치 (Central Processing Unit)',
    'RAM': '랜덤 액세스 메모리 (Random Access Memory)',
    'IoT': '사물인터넷 (Internet of Things)',
    'AR': '증강현실 (Augmented Reality)',
    'VR': '가상현실 (Virtual Reality)',
    'LLM': '대규모 언어 모델 (Large Language Model)',
    'RAG': '검색 증강 생성 (Retrieval-Augmented Generation)',
    'GEO': '생성형 엔진 최적화 (Generative Engine Optimization)',
    'MCP': '모델 컨텍스트 프로토콜 (Model Context Protocol)',
}


def extract_acronyms(content: str) -> dict:
    """콘텐츠에서 약어와 전문용어를 추출합니다.

    Args:
        content: 분석할 콘텐츠

    Returns:
        {
            "acronyms": [{"term": str, "definition": str, "count": int, "known": bool}],
            "summary": {"total": int, "known": int, "unknown": int},
            "glossary_markdown": str,
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'acronyms': [],
            'summary': {'total': 0, 'known': 0, 'unknown': 0},
            'glossary_markdown': '',
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    # 대문자 약어 추출 (2~6자) — 한국어 경계 대응
    uppercase_acronyms = _UPPERCASE_ACRONYM_RE.findall(content)

    # 빈도 계산
    freq = {}
    for acr in uppercase_acronyms:
        # 단일 문자나 너무 일반적인 단어 제외
        if len(acr) < 2:
            continue
        # 일반 영단어 제외 (전부 대문자가 아닌 것)
        if not acr.isupper() and acr not in _KNOWN_ACRONYMS:
            continue
        freq[acr] = freq.get(acr, 0) + 1

    # CamelCase 약어 (SaaS, DevOps 등)
    camel_terms = _CAMEL_TERM_RE.findall(content)
    for term in camel_terms:
        if term in _KNOWN_ACRONYMS:
            freq[term] = freq.get(term, 0) + 1

    # 결과 정리
    acronyms = []
    known_count = 0
    unknown_count = 0

    for term, count in sorted(freq.items(), key=lambda x: x[1], reverse=True):
        known = term in _KNOWN_ACRONYMS
        definition = _KNOWN_ACRONYMS.get(term, '정의를 확인해 주세요')
        acronyms.append({
            'term': term,
            'definition': definition,
            'count': count,
            'known': known,
        })
        if known:
            known_count += 1
        else:
            unknown_count += 1

    # 용어집 마크다운 생성
    glossary = _build_glossary_markdown(acronyms)

    # 제안
    suggestions = _generate_suggestions(acronyms, known_count, unknown_count)

    return {
        'acronyms': acronyms,
        'summary': {
            'total': len(acronyms),
            'known': known_count,
            'unknown': unknown_count,
        },
        'glossary_markdown': glossary,
        'suggestions': suggestions,
    }


def _build_glossary_markdown(acronyms: list) -> str:
    """용어집 마크다운을 생성합니다."""
    if not acronyms:
        return ''

    lines = ['## 용어집', '']
    for acr in acronyms:
        if acr['known']:
            lines.append(f'- **{acr["term"]}**: {acr["definition"]}')
        else:
            lines.append(f'- **{acr["term"]}**: _(정의 필요)_')

    return '\n'.join(lines)


def _generate_suggestions(acronyms: list, known: int, unknown: int) -> list:
    suggestions = []

    if not acronyms:
        suggestions.append('약어나 전문용어가 감지되지 않았습니다.')
        return suggestions

    if unknown > 0:
        suggestions.append(f'{unknown}개 약어의 정의가 불분명합니다. 처음 사용할 때 괄호 안에 풀어서 적어 주세요.')

    total = len(acronyms)
    if total > 10:
        suggestions.append(f'약어가 {total}개로 많습니다. 독자가 비전문가라면 용어집을 추가하세요.')

    # 정의 없이 사용된 약어
    undefined = [a for a in acronyms if not a['known']]
    if undefined:
        terms = ', '.join(a['term'] for a in undefined[:5])
        suggestions.append(f'정의가 필요한 약어: {terms}')

    if not suggestions:
        suggestions.append('약어가 적절히 사용되고 있습니다.')

    return suggestions
