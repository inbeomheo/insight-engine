"""
마크다운 각주(Footnote) 관리 서비스

Pandoc/CommonMark 확장 문법의 각주 `[^id]` 참조와
`[^id]: 설명` 정의를 파싱하여 렌더링·검증합니다.

기능:
- parse_footnotes: 참조·정의 추출
- validate_footnotes: 미정의 참조, 미사용 정의, 중복 정의 탐지
- render_footnotes_html: 본문 HTML 스니펫 + 각주 섹션 생성
- renumber_footnotes: ID를 1..N으로 재번호
"""
import logging
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# `[^id]` 또는 `[^1]` 참조 (정의 라인의 앞부분과 충돌 방지를 위해 뒤에 ':'가 오면 제외)
_REFERENCE_PATTERN = re.compile(r'\[\^([^\]]+)\](?!:)')
# 정의 시작 라인: `[^id]: 첫 줄 내용`. 후속 연속 라인(4칸 들여쓰기 또는 탭)은
# _extract_definitions()에서 별도로 병합합니다.
_DEFINITION_START_PATTERN = re.compile(r'^\[\^([^\]]+)\]:\s*(.*)$')
# parse에서 정의 라인 전체 영역을 본문에서 제거할 때 사용 (멀티라인 포함)
_DEFINITION_PATTERN = re.compile(
    r'^\[\^([^\]]+)\]:[^\n]*(?:\n(?:[ ]{4}|\t)[^\n]*)*',
    re.MULTILINE,
)

ALLOWED_ID_PATTERN = re.compile(r'^[A-Za-z0-9_\-]+$')


def parse_footnotes(content: str) -> dict:
    """콘텐츠에서 각주 참조와 정의를 추출합니다.

    Returns:
        {
            'references': [{'id': str, 'order': int, 'position': int}],
            'definitions': {id: text},
            'definition_order': [id, ...],  # 본문 등장 순서
        }
    """
    if not content:
        return {'references': [], 'definitions': {}, 'definition_order': []}

    # 먼저 정의를 수집 (멀티라인 continuation 지원)
    definitions: Dict[str, str] = {}
    definition_order: List[str] = []
    for fid, text in _extract_definitions(content):
        if fid in definitions:
            # 중복 정의는 validate 단계에서 보고 — 최초 정의만 보존
            continue
        definitions[fid] = text
        definition_order.append(fid)

    # 정의 라인을 제거한 본문에서 참조 추출 (정의 라인 내부 `[^id]:`가 참조로 잘못 잡히지 않도록)
    body_only = _DEFINITION_PATTERN.sub('', content)

    references: List[dict] = []
    for order, match in enumerate(_REFERENCE_PATTERN.finditer(body_only)):
        fid = match.group(1).strip()
        references.append({
            'id': fid,
            'order': order,
            'position': match.start(),
        })

    return {
        'references': references,
        'definitions': definitions,
        'definition_order': definition_order,
    }


def validate_footnotes(content: str) -> dict:
    """각주의 일관성을 검증합니다.

    감지 항목:
    - missing_definition: 참조되지만 정의가 없음
    - unused_definition: 정의되었지만 참조되지 않음
    - duplicate_definition: 같은 ID의 정의가 여러 번
    - invalid_id: ID가 허용 문자(A-Za-z0-9_-) 이외를 포함
    """
    parsed = parse_footnotes(content)
    references = parsed['references']
    definitions = parsed['definitions']

    ref_ids = [r['id'] for r in references]
    ref_set = set(ref_ids)
    def_set = set(definitions.keys())

    issues: List[dict] = []

    for fid in ref_set - def_set:
        issues.append({
            'type': 'missing_definition',
            'id': fid,
            'severity': 'error',
            'message': f'각주 [^{fid}]가 본문에 참조되지만 정의가 없습니다.',
        })

    for fid in def_set - ref_set:
        issues.append({
            'type': 'unused_definition',
            'id': fid,
            'severity': 'warning',
            'message': f'각주 [^{fid}]가 정의되었지만 어디서도 참조되지 않습니다.',
        })

    # 중복 정의 검출 (멀티라인 정의 기준 재스캔)
    seen: Dict[str, int] = {}
    for fid, _ in _extract_definitions(content or ''):
        seen[fid] = seen.get(fid, 0) + 1
    for fid, cnt in seen.items():
        if cnt > 1:
            issues.append({
                'type': 'duplicate_definition',
                'id': fid,
                'severity': 'error',
                'message': f'각주 [^{fid}] 정의가 {cnt}번 중복되어 있습니다.',
            })

    for fid in ref_set | def_set:
        if not ALLOWED_ID_PATTERN.match(fid):
            issues.append({
                'type': 'invalid_id',
                'id': fid,
                'severity': 'warning',
                'message': f'각주 ID "{fid}"에 허용되지 않는 문자가 포함되어 있습니다.',
            })

    error_count = sum(1 for i in issues if i['severity'] == 'error')

    return {
        'valid': error_count == 0,
        'reference_count': len(references),
        'definition_count': len(definitions),
        'issues': issues,
    }


def render_footnotes_html(content: str) -> dict:
    """마크다운 각주를 HTML로 변환합니다.

    본문의 `[^id]`는 `<sup><a>`로, 정의 라인은 제거 후
    문서 말미의 `<ol class="footnotes">` 섹션으로 이동합니다.

    주의: 이 함수는 전체 마크다운 렌더러가 아닙니다. 본문에 포함된
    원시 HTML(예: `<script>`)은 안전을 위해 모두 이스케이프됩니다.
    """
    parsed = parse_footnotes(content or '')
    definitions = parsed['definitions']
    references = parsed['references']

    # 참조 → 렌더링용 순번(1..N) 매핑 — 등장 순서, 정의가 있는 ID만
    id_to_number: Dict[str, int] = {}
    counter = 1
    for ref in references:
        if ref['id'] in id_to_number:
            continue
        if ref['id'] not in definitions:
            continue  # 미정의 참조는 원문 유지
        id_to_number[ref['id']] = counter
        counter += 1

    # 본문에서 정의 라인 제거
    body = _DEFINITION_PATTERN.sub('', content or '')
    # XSS 방지: 본문 전체를 먼저 이스케이프한 뒤 각주 참조만 태그로 치환.
    # `[^id]` 구조는 이스케이프로 변형되지 않음(괄호·대괄호 모두 안전).
    escaped_body = _html_escape(body)

    def _ref_sub(match: re.Match) -> str:
        fid = match.group(1).strip()
        num = id_to_number.get(fid)
        if num is None:
            # 정의 없음 → 이스케이프된 원문 유지
            return match.group(0)
        safe_id = _html_escape(fid)
        return (
            f'<sup class="footnote-ref"><a id="fnref-{safe_id}" href="#fn-{safe_id}">'
            f'{num}</a></sup>'
        )

    body_html = _REFERENCE_PATTERN.sub(_ref_sub, escaped_body).strip()

    # 각주 섹션 생성 (참조된 ID만, 번호 순)
    used_ids = [fid for fid, _ in sorted(id_to_number.items(), key=lambda kv: kv[1])]
    if not used_ids:
        return {'body_html': body_html, 'footnotes_html': '', 'count': 0}

    items = []
    for fid in used_ids:
        text = definitions.get(fid, '')
        safe_id = _html_escape(fid)
        safe_text = _html_escape(text)
        items.append(
            f'<li id="fn-{safe_id}">{safe_text} '
            f'<a href="#fnref-{safe_id}" class="footnote-backref">↩</a></li>'
        )
    footnotes_html = '<ol class="footnotes">\n' + '\n'.join(items) + '\n</ol>'

    return {'body_html': body_html, 'footnotes_html': footnotes_html, 'count': len(used_ids)}


def renumber_footnotes(content: str) -> dict:
    """각주 ID를 본문 등장 순서대로 1..N으로 재번호합니다.

    미정의 참조는 그대로 두고, 매핑이 있는 참조·정의만 치환합니다.
    """
    parsed = parse_footnotes(content or '')
    references = parsed['references']
    definitions = parsed['definitions']

    # 본문 등장 순서대로 고유 ID 수집 (정의 있는 것만)
    mapping: Dict[str, str] = {}
    counter = 1
    for ref in references:
        fid = ref['id']
        if fid in mapping or fid not in definitions:
            continue
        mapping[fid] = str(counter)
        counter += 1

    if not mapping:
        return {'content': content or '', 'mapping': {}}

    def _ref_sub(match: re.Match) -> str:
        fid = match.group(1).strip()
        new_id = mapping.get(fid)
        return f'[^{new_id}]' if new_id else match.group(0)

    # 정의 라인의 선두 `[^id]:`만 치환 (continuation 라인은 그대로 보존)
    def _def_start_sub(match: re.Match) -> str:
        fid = match.group(1).strip()
        rest = match.group(2)
        new_id = mapping.get(fid)
        return f'[^{new_id}]:{rest}' if new_id else match.group(0)

    updated = _REFERENCE_PATTERN.sub(_ref_sub, content or '')
    updated = re.sub(
        r'^\[\^([^\]]+)\]:(.*)$',
        _def_start_sub,
        updated,
        flags=re.MULTILINE,
    )

    return {'content': updated, 'mapping': mapping}


def _html_escape(text: str) -> str:
    """HTML 특수문자 이스케이프."""
    return (
        text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;')
    )


def _extract_definitions(content: str) -> List[Tuple[str, str]]:
    """`[^id]: 내용` + 들여쓰기된 continuation 라인들을 하나의 정의로 묶습니다.

    CommonMark/Pandoc 확장 규칙에 따라 다음 라인이 4칸 이상 들여쓰여 있거나
    탭으로 시작하면 이전 정의의 연장으로 간주합니다.
    """
    if not content:
        return []

    lines = content.split('\n')
    results: List[Tuple[str, str]] = []
    i = 0
    while i < len(lines):
        match = _DEFINITION_START_PATTERN.match(lines[i])
        if not match:
            i += 1
            continue
        fid = match.group(1).strip()
        parts = [match.group(2).strip()]
        j = i + 1
        while j < len(lines):
            next_line = lines[j]
            if next_line.startswith('    ') or next_line.startswith('\t'):
                parts.append(next_line.lstrip().rstrip())
                j += 1
                continue
            # 빈 라인은 잠정적으로 포함, 단 그 다음 라인이 계속 들여쓰여 있어야 함
            if next_line.strip() == '' and j + 1 < len(lines) and (
                lines[j + 1].startswith('    ') or lines[j + 1].startswith('\t')
            ):
                parts.append('')
                j += 1
                continue
            break
        combined = '\n'.join(p for p in parts if p is not None).strip()
        results.append((fid, combined))
        i = j
    return results
