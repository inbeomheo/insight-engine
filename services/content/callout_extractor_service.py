"""
콜아웃(Callout) 블록 추출 서비스

마크다운에서 자주 쓰이는 콜아웃/어드모니션 패턴을 감지하고 분류합니다.

지원 문법:
1. GitHub/Obsidian 스타일: `> [!NOTE]`, `> [!TIP]`, `> [!WARNING]`
2. Docusaurus 스타일:      `:::tip Title`, `:::note`, `:::caution`
3. 관습 인용 스타일:        `> **Note:**`, `> **Warning:**`
"""
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

# 허용 타입(대문자 정규화 기준)
VALID_TYPES = {
    'NOTE', 'TIP', 'INFO', 'WARNING', 'CAUTION', 'DANGER',
    'IMPORTANT', 'SUCCESS', 'QUOTE', 'EXAMPLE',
}

# GitHub/Obsidian: `> [!TYPE]` + 이어지는 `> ...` 라인들
_GITHUB_HEADER = re.compile(r'^>\s*\[!(?P<type>[A-Z]+)\](?P<title>.*)$')
# Docusaurus/MkDocs Material: `:::type title` ~ `:::`
_DOCUSAURUS_OPEN = re.compile(r'^:::(?P<type>[a-zA-Z]+)(?P<title>.*)$')
_DOCUSAURUS_CLOSE = re.compile(r'^:::\s*$')
# 관습 인용: `> **Type:** 내용...`
_BOLD_HEADER = re.compile(r'^>\s*\*\*(?P<type>[A-Za-z]+):?\*\*\s*(?P<body>.*)$')


def extract_callouts(content: str) -> dict:
    """콘텐츠에서 모든 콜아웃 블록을 추출합니다.

    Returns:
        {
            'callouts': [{
                'type': str,     # 'note'|'tip'|'warning'|'caution'|...
                'title': str,    # 선택적 제목 (없으면 '')
                'body': str,     # 콜아웃 본문(trim)
                'style': 'github'|'docusaurus'|'bold',
                'line': int,     # 시작 라인(1-based)
            }],
            'count': int,
            'by_type': {type: count},
        }
    """
    if not content:
        return {'callouts': [], 'count': 0, 'by_type': {}}

    lines = content.split('\n')
    callouts: List[dict] = []
    i = 0
    in_code = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 코드 블록 내부는 건너뜀
        if stripped.startswith('```') or stripped.startswith('~~~'):
            in_code = not in_code
            i += 1
            continue
        if in_code:
            i += 1
            continue

        # 1) GitHub/Obsidian: `> [!TYPE]`
        gh_match = _GITHUB_HEADER.match(stripped)
        if gh_match:
            ctype = gh_match.group('type').lower()
            title = gh_match.group('title').strip()
            body_lines = []
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith('>'):
                body_lines.append(lines[j].lstrip('>').lstrip())
                j += 1
            callouts.append({
                'type': ctype,
                'title': title,
                'body': '\n'.join(body_lines).strip(),
                'style': 'github',
                'line': i + 1,
            })
            i = j
            continue

        # 2) Docusaurus: `:::type`
        dc_match = _DOCUSAURUS_OPEN.match(stripped)
        if dc_match:
            ctype = dc_match.group('type').lower()
            title = dc_match.group('title').strip()
            body_lines = []
            j = i + 1
            while j < len(lines) and not _DOCUSAURUS_CLOSE.match(lines[j].strip()):
                body_lines.append(lines[j])
                j += 1
            callouts.append({
                'type': ctype,
                'title': title,
                'body': '\n'.join(body_lines).strip(),
                'style': 'docusaurus',
                'line': i + 1,
            })
            # `:::` 닫힘 라인도 건너뛰기
            i = j + 1 if j < len(lines) else j
            continue

        # 3) Bold header: `> **Type:**`
        bold_match = _BOLD_HEADER.match(stripped)
        if bold_match:
            raw_type = bold_match.group('type').upper()
            ctype = raw_type.lower() if raw_type in VALID_TYPES else 'note'
            first_body = bold_match.group('body').strip()
            body_lines = [first_body] if first_body else []
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith('>'):
                body_lines.append(lines[j].lstrip('>').lstrip())
                j += 1
            callouts.append({
                'type': ctype,
                'title': '',
                'body': '\n'.join(body_lines).strip(),
                'style': 'bold',
                'line': i + 1,
            })
            i = j
            continue

        i += 1

    by_type: dict = {}
    for c in callouts:
        by_type[c['type']] = by_type.get(c['type'], 0) + 1

    return {'callouts': callouts, 'count': len(callouts), 'by_type': by_type}


def render_callouts_html(content: str) -> dict:
    """콘텐츠의 콜아웃을 HTML `<aside>` 블록으로 변환합니다.

    본문 내 원시 HTML은 XSS 방지를 위해 이스케이프되며, 콜아웃 블록은
    `<aside class="callout callout-TYPE">` 형식으로 마크업됩니다.
    """
    parsed = extract_callouts(content or '')
    callouts = parsed['callouts']
    rendered_blocks = [_callout_to_html(c) for c in callouts]
    return {
        'count': parsed['count'],
        'by_type': parsed['by_type'],
        'blocks_html': rendered_blocks,
    }


def _callout_to_html(callout: dict) -> str:
    ctype = _html_escape(callout.get('type', 'note'))
    title = _html_escape(callout.get('title', ''))
    body = _html_escape(callout.get('body', ''))
    title_tag = f'<div class="callout-title">{title}</div>' if title else ''
    body_tag = f'<div class="callout-body">{body}</div>' if body else ''
    return f'<aside class="callout callout-{ctype}">{title_tag}{body_tag}</aside>'


def _html_escape(text: str) -> str:
    return (
        text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;')
    )


def suggest_callout_for_paragraph(paragraph: str) -> Optional[str]:
    """문단의 시작 키워드를 기반으로 어떤 콜아웃 타입이 적합한지 제안합니다.

    규칙 기반(AI 없음). None을 반환하면 추천 없음을 의미.
    """
    if not paragraph:
        return None
    text = paragraph.strip().lower()
    keyword_map = [
        (('주의', 'caution', '조심'), 'caution'),
        (('경고', 'warning', 'warn'), 'warning'),
        (('위험', 'danger'), 'danger'),
        (('참고', 'note', '노트'), 'note'),
        (('팁', 'tip', '힌트', 'hint'), 'tip'),
        (('중요', 'important', 'critical'), 'important'),
        (('예시', 'example', 'for example'), 'example'),
        (('성공', 'success', '완료'), 'success'),
    ]
    for keywords, ctype in keyword_map:
        if any(text.startswith(k) or f'**{k}**' in text or f'{k}:' in text for k in keywords):
            return ctype
    return None
