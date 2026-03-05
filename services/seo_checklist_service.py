"""SEO 체크리스트 서비스 (F8-13)

콘텐츠의 SEO 품질을 다항목 체크리스트로 검사합니다.
각 항목은 통과(pass)/경고(warn)/실패(fail) 중 하나를 반환합니다.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 체크 결과 상수
PASS = 'pass'
WARN = 'warn'
FAIL = 'fail'


def _check_title_length(title: str) -> dict:
    """제목 길이: 30~60자 권장."""
    n = len(title)
    if 30 <= n <= 60:
        return {'id': 'title_length', 'status': PASS, 'msg': f'제목 길이 적절 ({n}자)'}
    elif n < 30:
        return {'id': 'title_length', 'status': WARN, 'msg': f'제목이 너무 짧습니다 ({n}자, 권장 30~60자)'}
    else:
        return {'id': 'title_length', 'status': WARN, 'msg': f'제목이 너무 깁니다 ({n}자, 권장 30~60자)'}


def _check_content_length(content: str) -> dict:
    """본문 길이: 300자 이상 권장."""
    n = len(content.strip())
    if n >= 1000:
        return {'id': 'content_length', 'status': PASS, 'msg': f'본문 길이 충분 ({n}자)'}
    elif n >= 300:
        return {'id': 'content_length', 'status': WARN, 'msg': f'본문이 다소 짧습니다 ({n}자, 권장 1000자+)'}
    else:
        return {'id': 'content_length', 'status': FAIL, 'msg': f'본문이 너무 짧습니다 ({n}자, 최소 300자)'}


def _check_heading(content: str) -> dict:
    """H1/H2 헤딩 존재 여부."""
    has_h1 = bool(re.search(r'^#{1}\s+\S', content, re.MULTILINE))
    has_h2 = bool(re.search(r'^#{2}\s+\S', content, re.MULTILINE))
    if has_h1 and has_h2:
        return {'id': 'headings', 'status': PASS, 'msg': 'H1, H2 헤딩 포함'}
    elif has_h1 or has_h2:
        return {'id': 'headings', 'status': WARN, 'msg': 'H1 또는 H2 헤딩만 존재 (둘 다 권장)'}
    else:
        return {'id': 'headings', 'status': FAIL, 'msg': '헤딩(H1/H2) 없음'}


def _check_links(content: str) -> dict:
    """내부/외부 링크 존재 여부."""
    links = re.findall(r'\[.+?\]\(https?://.+?\)', content)
    if len(links) >= 2:
        return {'id': 'links', 'status': PASS, 'msg': f'링크 {len(links)}개 포함'}
    elif len(links) == 1:
        return {'id': 'links', 'status': WARN, 'msg': '링크 1개 (2개 이상 권장)'}
    else:
        return {'id': 'links', 'status': WARN, 'msg': '링크 없음 (관련 링크 추가 권장)'}


def _check_keyword_density(title: str, content: str) -> dict:
    """제목의 주요 키워드가 본문에 등장하는지 확인."""
    if not title:
        return {'id': 'keyword_density', 'status': WARN, 'msg': '제목 없음'}
    # 제목 첫 단어를 키워드로 사용
    keyword = title.split()[0].lower() if title.split() else ''
    if not keyword:
        return {'id': 'keyword_density', 'status': WARN, 'msg': '키워드 추출 불가'}
    count = content.lower().count(keyword)
    if count >= 3:
        return {'id': 'keyword_density', 'status': PASS, 'msg': f'키워드 "{keyword}" {count}회 등장'}
    elif count >= 1:
        return {'id': 'keyword_density', 'status': WARN, 'msg': f'키워드 "{keyword}" {count}회 (3회 이상 권장)'}
    else:
        return {'id': 'keyword_density', 'status': FAIL, 'msg': f'키워드 "{keyword}" 본문 미포함'}


def _check_meta_description(meta: dict) -> dict:
    """메타 설명 존재 및 길이 확인."""
    desc = meta.get('description', '') if meta else ''
    n = len(desc)
    if 120 <= n <= 160:
        return {'id': 'meta_description', 'status': PASS, 'msg': f'메타 설명 적절 ({n}자)'}
    elif n > 0:
        return {'id': 'meta_description', 'status': WARN, 'msg': f'메타 설명 길이 조정 필요 ({n}자, 권장 120~160자)'}
    else:
        return {'id': 'meta_description', 'status': WARN, 'msg': '메타 설명 없음 (SEO에 권장)'}


def run_checklist(
    title: str,
    content: str,
    meta: Optional[dict] = None,
) -> dict:
    """SEO 체크리스트 전체를 실행합니다.

    Returns:
        {
            'score': 0~100,
            'grade': 'A'|'B'|'C'|'D',
            'checks': [{'id', 'status', 'msg'}, ...]
        }
    """
    checks = [
        _check_title_length(title),
        _check_content_length(content),
        _check_heading(content),
        _check_links(content),
        _check_keyword_density(title, content),
        _check_meta_description(meta or {}),
    ]

    weights = {PASS: 2, WARN: 1, FAIL: 0}
    max_score = len(checks) * 2
    score_raw = sum(weights[c['status']] for c in checks)
    score = round(score_raw / max_score * 100)

    if score >= 80:
        grade = 'A'
    elif score >= 60:
        grade = 'B'
    elif score >= 40:
        grade = 'C'
    else:
        grade = 'D'

    return {'score': score, 'grade': grade, 'checks': checks}
