"""
대량 수정 큐 서비스

여러 콘텐츠에 대해 규칙 기반 수정 제안(diff)을 생성하고,
승인된 제안만 선택적으로 적용합니다.
순수 파이썬, AI API 호출 없음.
"""
import re
import uuid
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EditProposal:
    """수정 제안 데이터."""
    proposal_id: str
    content_id: str
    original: str
    proposed: str
    edit_type: str  # "seo", "grammar", "style", "compliance"
    diff_summary: str
    confidence: float  # 0.0 ~ 1.0


# ── SEO 규칙 ──

_SEO_TITLE_MAX_LEN = 60

# 메타 설명이 없는 콘텐츠 패턴
_META_DESC_PATTERN = re.compile(
    r'(?:meta\s*description|메타\s*설명)\s*[:：]\s*\S+', re.IGNORECASE
)

# 중복 키워드 패턴 (동일 단어 3회 이상 연속)
_KEYWORD_STUFFING = re.compile(r'\b(\w{2,})\b(?:\s+\1){2,}', re.IGNORECASE)


# ── 문법 규칙 ──

# 이중 공백
_DOUBLE_SPACE = re.compile(r'  +')

# 반복 마침표
_MULTI_PERIOD = re.compile(r'\.{4,}')

# 괄호 불일치 (열린 괄호 수 ≠ 닫힌 괄호 수)
_OPEN_PAREN = re.compile(r'[(\[{]')
_CLOSE_PAREN = re.compile(r'[)\]}]')


# ── 스타일 규칙 ──

# 과도한 느낌표
_EXCESSIVE_EXCLAIM = re.compile(r'!{2,}')

# 과도한 물음표
_EXCESSIVE_QUESTION = re.compile(r'\?{3,}')

# 비격식 표현 (콘텐츠 발행물 기준)
_INFORMAL_PATTERNS = [
    re.compile(r'ㅋ{2,}'),
    re.compile(r'ㅎ{2,}'),
    re.compile(r'ㅠ{2,}'),
    re.compile(r'ㅜ{2,}'),
]


# ── 규정 준수(Compliance) 규칙 ──

# 가격/할인 언급인데 조건 미표기
_PRICE_MENTION = re.compile(r'(?:할인|무료|0원|세일|특가)', re.IGNORECASE)
_CONDITION_MENTION = re.compile(r'(?:조건|기간|한정|제한|약관)', re.IGNORECASE)

# 절대적 보증 표현
_ABSOLUTE_GUARANTEE = re.compile(
    r'(?:100%|절대|반드시|확실히|보장합니다|틀림없)', re.IGNORECASE
)


def _generate_id() -> str:
    """고유 제안 ID 생성."""
    return uuid.uuid4().hex[:12]


def _check_seo(content_id: str, content: str) -> List[EditProposal]:
    """SEO 관련 수정 제안 생성."""
    proposals = []
    lines = content.split('\n')
    matches = 0

    # 제목(첫 줄) 길이 체크
    if lines:
        title = lines[0].strip().lstrip('#').strip()
        if len(title) > _SEO_TITLE_MAX_LEN:
            truncated = title[:_SEO_TITLE_MAX_LEN - 3] + '...'
            matches += 1
            proposals.append(EditProposal(
                proposal_id=_generate_id(),
                content_id=content_id,
                original=title,
                proposed=truncated,
                edit_type='seo',
                diff_summary=f'제목이 {len(title)}자로 {_SEO_TITLE_MAX_LEN}자를 초과합니다. 축약을 권장합니다.',
                confidence=round(min(1.0, 0.5 + matches * 0.15), 2),
            ))

    # 메타 설명 누락
    if not _META_DESC_PATTERN.search(content):
        matches += 1
        proposals.append(EditProposal(
            proposal_id=_generate_id(),
            content_id=content_id,
            original='',
            proposed='meta description: [콘텐츠 요약을 150자 이내로 작성하세요]',
            edit_type='seo',
            diff_summary='메타 설명이 없습니다. 검색 노출을 위해 추가를 권장합니다.',
            confidence=round(min(1.0, 0.5 + matches * 0.15), 2),
        ))

    # 키워드 스터핑
    stuffing = _KEYWORD_STUFFING.findall(content)
    if stuffing:
        matches += 1
        for kw in stuffing[:3]:
            proposals.append(EditProposal(
                proposal_id=_generate_id(),
                content_id=content_id,
                original=kw,
                proposed=kw,
                edit_type='seo',
                diff_summary=f'키워드 "{kw}"가 과도하게 반복됩니다. 키워드 스터핑은 SEO에 불리합니다.',
                confidence=round(min(1.0, 0.5 + matches * 0.15), 2),
            ))

    # confidence 재계산 (매칭 수 기반)
    for p in proposals:
        p.confidence = round(min(1.0, 0.5 + matches * 0.15), 2)

    return proposals


def _check_grammar(content_id: str, content: str) -> List[EditProposal]:
    """문법 관련 수정 제안 생성."""
    proposals = []
    matches = 0

    # 이중 공백
    double_spaces = list(_DOUBLE_SPACE.finditer(content))
    if double_spaces:
        matches += 1
        fixed = _DOUBLE_SPACE.sub(' ', content)
        proposals.append(EditProposal(
            proposal_id=_generate_id(),
            content_id=content_id,
            original=content,
            proposed=fixed,
            edit_type='grammar',
            diff_summary=f'이중 공백이 {len(double_spaces)}곳에서 발견되었습니다.',
            confidence=round(min(1.0, 0.5 + matches * 0.15), 2),
        ))

    # 반복 마침표
    multi_periods = list(_MULTI_PERIOD.finditer(content))
    if multi_periods:
        matches += 1
        fixed_content = _MULTI_PERIOD.sub('...', content)
        proposals.append(EditProposal(
            proposal_id=_generate_id(),
            content_id=content_id,
            original=content,
            proposed=fixed_content,
            edit_type='grammar',
            diff_summary=f'과도한 말줄임표({len(multi_periods)}곳)를 정규화합니다.',
            confidence=round(min(1.0, 0.5 + matches * 0.15), 2),
        ))

    # 괄호 불일치
    open_count = len(_OPEN_PAREN.findall(content))
    close_count = len(_CLOSE_PAREN.findall(content))
    if open_count != close_count:
        matches += 1
        proposals.append(EditProposal(
            proposal_id=_generate_id(),
            content_id=content_id,
            original=f'열린 괄호 {open_count}개, 닫힌 괄호 {close_count}개',
            proposed=f'괄호 수를 일치시켜야 합니다.',
            edit_type='grammar',
            diff_summary=f'괄호 불일치: 열림 {open_count}개 vs 닫힘 {close_count}개.',
            confidence=round(min(1.0, 0.5 + matches * 0.15), 2),
        ))

    for p in proposals:
        p.confidence = round(min(1.0, 0.5 + matches * 0.15), 2)

    return proposals


def _check_style(content_id: str, content: str) -> List[EditProposal]:
    """스타일 관련 수정 제안 생성."""
    proposals = []
    matches = 0

    # 과도한 느낌표
    exclaims = list(_EXCESSIVE_EXCLAIM.finditer(content))
    if exclaims:
        matches += 1
        fixed = _EXCESSIVE_EXCLAIM.sub('!', content)
        proposals.append(EditProposal(
            proposal_id=_generate_id(),
            content_id=content_id,
            original=content,
            proposed=fixed,
            edit_type='style',
            diff_summary=f'과도한 느낌표({len(exclaims)}곳)를 단일 느낌표로 정규화합니다.',
            confidence=round(min(1.0, 0.5 + matches * 0.15), 2),
        ))

    # 과도한 물음표
    questions = list(_EXCESSIVE_QUESTION.finditer(content))
    if questions:
        matches += 1
        fixed = _EXCESSIVE_QUESTION.sub('?', content)
        proposals.append(EditProposal(
            proposal_id=_generate_id(),
            content_id=content_id,
            original=content,
            proposed=fixed,
            edit_type='style',
            diff_summary=f'과도한 물음표({len(questions)}곳)를 정규화합니다.',
            confidence=round(min(1.0, 0.5 + matches * 0.15), 2),
        ))

    # 비격식 표현
    informal_found = []
    for pat in _INFORMAL_PATTERNS:
        informal_found.extend(pat.findall(content))
    if informal_found:
        matches += 1
        proposals.append(EditProposal(
            proposal_id=_generate_id(),
            content_id=content_id,
            original=', '.join(informal_found[:5]),
            proposed='(비격식 표현 제거 권장)',
            edit_type='style',
            diff_summary=f'비격식 표현이 {len(informal_found)}개 발견되었습니다.',
            confidence=round(min(1.0, 0.5 + matches * 0.15), 2),
        ))

    for p in proposals:
        p.confidence = round(min(1.0, 0.5 + matches * 0.15), 2)

    return proposals


def _check_compliance(content_id: str, content: str) -> List[EditProposal]:
    """규정 준수 관련 수정 제안 생성."""
    proposals = []
    matches = 0

    # 가격 언급 + 조건 미표기
    has_price = bool(_PRICE_MENTION.search(content))
    has_condition = bool(_CONDITION_MENTION.search(content))
    if has_price and not has_condition:
        matches += 1
        proposals.append(EditProposal(
            proposal_id=_generate_id(),
            content_id=content_id,
            original=content,
            proposed=content + '\n\n※ 상기 가격/할인은 특정 조건 하에 적용됩니다. 자세한 내용은 약관을 확인하세요.',
            edit_type='compliance',
            diff_summary='가격/할인 언급이 있으나 적용 조건이 명시되지 않았습니다.',
            confidence=round(min(1.0, 0.5 + matches * 0.15), 2),
        ))

    # 절대적 보증 표현
    absolutes = list(_ABSOLUTE_GUARANTEE.finditer(content))
    if absolutes:
        matches += 1
        expressions = [m.group() for m in absolutes[:3]]
        proposals.append(EditProposal(
            proposal_id=_generate_id(),
            content_id=content_id,
            original=', '.join(expressions),
            proposed='(절대적 표현을 완화하세요)',
            edit_type='compliance',
            diff_summary=f'절대적 보증 표현({", ".join(expressions)})이 규정 위반 소지가 있습니다.',
            confidence=round(min(1.0, 0.5 + matches * 0.15), 2),
        ))

    for p in proposals:
        p.confidence = round(min(1.0, 0.5 + matches * 0.15), 2)

    return proposals


# ── edit_type → 검사 함수 매핑 ──
_CHECKERS = {
    'seo': _check_seo,
    'grammar': _check_grammar,
    'style': _check_style,
    'compliance': _check_compliance,
}


def queue_bulk_edits(
    contents: list,
    edit_type: str = 'seo',
) -> List[EditProposal]:
    """여러 콘텐츠에 대해 규칙 기반 수정 제안을 생성합니다.

    Args:
        contents: [{"id": str, "text": str}, ...] 형태의 콘텐츠 목록
        edit_type: 수정 유형 ("seo", "grammar", "style", "compliance")

    Returns:
        EditProposal 목록
    """
    if not contents:
        return []

    checker = _CHECKERS.get(edit_type)
    if checker is None:
        raise ValueError(f'지원하지 않는 edit_type: {edit_type}. 가능한 값: {list(_CHECKERS.keys())}')

    proposals = []
    for item in contents:
        content_id = item.get('id', _generate_id())
        text = item.get('text', '')
        if not text or not text.strip():
            continue
        proposals.extend(checker(content_id, text))

    return proposals


def apply_proposals(
    proposals: List[EditProposal],
    approved_ids: List[str],
) -> list:
    """승인된 제안만 적용하여 결과를 반환합니다.

    Args:
        proposals: 전체 제안 목록
        approved_ids: 승인된 proposal_id 목록

    Returns:
        [{"proposal_id": str, "applied": bool, "result": str}, ...]
    """
    if not proposals:
        return []

    approved_set = set(approved_ids or [])
    results = []

    for p in proposals:
        applied = p.proposal_id in approved_set
        results.append({
            'proposal_id': p.proposal_id,
            'content_id': p.content_id,
            'edit_type': p.edit_type,
            'applied': applied,
            'result': p.proposed if applied else p.original,
            'diff_summary': p.diff_summary,
        })

    return results
