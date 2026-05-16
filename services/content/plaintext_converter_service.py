"""
마크다운 → 순수 텍스트 변환 서비스

모든 마크다운 서식을 제거하고 순수 텍스트를 반환합니다.
복사/붙여넣기, 이메일, 메신저 전송에 적합.
"""
import logging
import re

logger = logging.getLogger(__name__)

# 제거 패턴 (순서 중요)
_CODE_BLOCK = re.compile(r'```[\s\S]*?```')
_INLINE_CODE = re.compile(r'`([^`]+)`')
_IMAGE = re.compile(r'!\[([^\]]*)\]\([^)]+\)')
_LINK = re.compile(r'\[([^\]]+)\]\([^)]+\)')
_HEADING = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_BOLD_ITALIC = re.compile(r'\*{1,3}([^*]+?)\*{1,3}')
_STRIKETHROUGH = re.compile(r'~~(.+?)~~')
_BLOCKQUOTE = re.compile(r'^>\s*', re.MULTILINE)
_HR = re.compile(r'^[-*_]{3,}\s*$', re.MULTILINE)
_HTML_TAG = re.compile(r'<[^>]+>')
_LIST_BULLET = re.compile(r'^\s*[-*•]\s+', re.MULTILINE)
_LIST_NUMBERED = re.compile(r'^\s*\d+[.)]\s+', re.MULTILINE)
_TABLE_SEPARATOR = re.compile(r'^\|?[-:|\s]+\|?\s*$', re.MULTILINE)
_TABLE_PIPE = re.compile(r'\|')
_MULTI_SPACE = re.compile(r'[ \t]{2,}')
_MULTI_NEWLINE = re.compile(r'\n{3,}')


def convert_to_plaintext(content: str, preserve_structure: bool = True) -> dict:
    """마크다운을 순수 텍스트로 변환합니다.

    Args:
        content: 마크다운 콘텐츠
        preserve_structure: 문단/줄바꿈 구조 유지 여부

    Returns:
        {
            'text': str,
            'char_count': int,
            'line_count': int,
            'removed_elements': {'images': int, 'links': int, 'code_blocks': int, ...},
        }
    """
    if not content or not content.strip():
        return _empty_result()

    text = content.strip()
    removed = {
        'images': len(_IMAGE.findall(text)),
        'links': len(_LINK.findall(text)),
        'code_blocks': len(_CODE_BLOCK.findall(text)),
        'html_tags': len(_HTML_TAG.findall(text)),
    }

    # 코드 블록 → 코드 내용만 남김
    text = _CODE_BLOCK.sub(_extract_code_content, text)

    # 인라인 코드 → 텍스트만
    text = _INLINE_CODE.sub(r'\1', text)

    # 이미지 → alt 텍스트만
    text = _IMAGE.sub(r'\1', text)

    # 링크 → 링크 텍스트만
    text = _LINK.sub(r'\1', text)

    # HTML 태그 제거
    text = _HTML_TAG.sub('', text)

    # 헤딩 기호 제거
    text = _HEADING.sub('', text)

    # 볼드/이탤릭/취소선 → 텍스트만
    text = _BOLD_ITALIC.sub(r'\1', text)
    text = _STRIKETHROUGH.sub(r'\1', text)

    # 인용 기호 제거
    text = _BLOCKQUOTE.sub('', text)

    # 수평선 제거
    text = _HR.sub('', text)

    # 리스트 기호 → 대시로 통일 또는 제거
    if preserve_structure:
        text = _LIST_BULLET.sub('- ', text)
        text = _LIST_NUMBERED.sub('- ', text)
    else:
        text = _LIST_BULLET.sub('', text)
        text = _LIST_NUMBERED.sub('', text)

    # 테이블 정리
    text = _TABLE_SEPARATOR.sub('', text)
    text = _TABLE_PIPE.sub(' ', text)

    # 정리
    text = _MULTI_SPACE.sub(' ', text)
    text = _MULTI_NEWLINE.sub('\n\n', text)
    text = text.strip()

    lines = [l for l in text.split('\n') if l.strip()] if not preserve_structure else text.split('\n')

    return {
        'text': text,
        'char_count': len(text),
        'line_count': len(lines),
        'removed_elements': removed,
    }


def _extract_code_content(match):
    """코드 블록에서 코드 내용만 추출합니다."""
    block = match.group(0)
    # ``` 제거, 언어 지정자 제거
    lines = block.split('\n')
    if lines:
        lines = lines[1:]  # 첫 줄 (```) 제거
    if lines and lines[-1].strip() == '```':
        lines = lines[:-1]  # 마지막 줄 (```) 제거
    return '\n'.join(lines)


def _empty_result() -> dict:
    return {
        'text': '',
        'char_count': 0,
        'line_count': 0,
        'removed_elements': {'images': 0, 'links': 0, 'code_blocks': 0, 'html_tags': 0},
    }
