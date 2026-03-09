"""
llms.txt 생성 및 검증 서비스

웹사이트 페이지 메타데이터를 기반으로 llms.txt 파일을 자동 생성하고,
기존 llms.txt 파일의 형식과 내용을 검증합니다.

llms.txt 형식 참조: https://llmstxt.org/
"""
import re
import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class PageMeta:
    """페이지 메타데이터"""
    url: str
    title: str
    description: str
    content_type: str  # "article" | "product" | "faq" | "guide"

    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            'url': self.url,
            'title': self.title,
            'description': self.description,
            'content_type': self.content_type,
        }


@dataclass
class ValidationIssue:
    """llms.txt 검증 이슈"""
    line: int
    severity: str    # "error" | "warning"
    message: str

    def to_dict(self) -> dict:
        """딕셔너리 변환"""
        return {
            'line': self.line,
            'severity': self.severity,
            'message': self.message,
        }


# 유효한 content_type 값
VALID_CONTENT_TYPES = {'article', 'product', 'faq', 'guide'}

# content_type별 섹션 제목
_SECTION_TITLES: dict[str, str] = {
    'guide': 'Guides',
    'article': 'Articles',
    'product': 'Products',
    'faq': 'FAQ',
}

# content_type별 정렬 순서 (가이드 → FAQ → 기사 → 제품)
_SECTION_ORDER: dict[str, int] = {
    'guide': 0,
    'faq': 1,
    'article': 2,
    'product': 3,
}

# URL 형식 검증 패턴
_URL_PATTERN = re.compile(r'^https?://')

# llms.txt 링크 라인 패턴: - [제목](URL): 설명
_LINK_LINE_RE = re.compile(r'^-\s+\[([^\]]+)\]\(([^)]+)\)(?::\s*(.+))?$')

# 섹션 헤더 패턴: ## 제목
_SECTION_HEADER_RE = re.compile(r'^##\s+(.+)$')

# 메인 제목 패턴: # 제목
_MAIN_TITLE_RE = re.compile(r'^#\s+(.+)$')

# 블록인용문 패턴: > 텍스트
_BLOCKQUOTE_RE = re.compile(r'^>\s*(.*)$')


def generate_llms_txt(
    pages: list[dict],
    site_title: str = '',
    site_description: str = '',
) -> str:
    """페이지 메타데이터에서 llms.txt를 자동 생성합니다.

    llms.txt 표준 형식:
    - # 사이트 제목
    - > 사이트 설명 (블록인용문)
    - ## 섹션 (content_type별 그룹)
    - - [제목](URL): 설명

    Args:
        pages: 페이지 메타데이터 딕셔너리 목록
            각 항목에 'url', 'title', 'description', 'content_type' 필수
        site_title: 사이트 제목 (생략 시 첫 페이지 도메인 사용)
        site_description: 사이트 설명 (블록인용문, 생략 가능)

    Returns:
        llms.txt 형식 문자열

    Raises:
        ValueError: pages가 비어있거나 필수 필드 누락
    """
    if not pages:
        raise ValueError('pages 목록이 비어있습니다.')

    # PageMeta로 변환 및 검증
    page_metas = _parse_pages(pages)

    # 사이트 제목 결정
    if not site_title:
        first_url = page_metas[0].url
        parsed = urlparse(first_url)
        site_title = parsed.netloc or 'My Site'

    # llms.txt 빌드
    lines: list[str] = []

    # 메인 제목
    lines.append(f'# {site_title}')
    lines.append('')

    # 사이트 설명 (블록인용문)
    if site_description:
        lines.append(f'> {site_description}')
        lines.append('')

    # content_type별 섹션 그룹화
    sections = _group_by_content_type(page_metas)

    # 정렬된 순서로 섹션 출력
    sorted_types = sorted(sections.keys(), key=lambda t: _SECTION_ORDER.get(t, 99))

    for content_type in sorted_types:
        section_pages = sections[content_type]
        section_title = _SECTION_TITLES.get(content_type, content_type.capitalize())

        lines.append(f'## {section_title}')
        lines.append('')

        for page in section_pages:
            desc_part = f': {page.description}' if page.description else ''
            lines.append(f'- [{page.title}]({page.url}){desc_part}')

        lines.append('')

    result = '\n'.join(lines).rstrip() + '\n'

    logger.info('llms.txt 생성 완료: %d개 페이지, %d개 섹션', len(page_metas), len(sections))

    return result


def validate_llms_txt(content: str) -> list[ValidationIssue]:
    """llms.txt 내용을 검증합니다.

    검증 항목:
    - 메인 제목(# ) 존재 여부
    - 섹션 헤더(## ) 존재 여부
    - 링크 라인 형식 (- [제목](URL))
    - URL 형식 유효성
    - 빈 섹션 감지
    - 중복 URL 감지

    Args:
        content: llms.txt 파일 내용

    Returns:
        ValidationIssue 목록 (이슈 없으면 빈 리스트)
    """
    if not content or not content.strip():
        return [ValidationIssue(line=0, severity='error', message='파일 내용이 비어있습니다.')]

    issues: list[ValidationIssue] = []
    lines = content.split('\n')

    has_main_title = False
    has_section = False
    has_links = False
    seen_urls: dict[str, int] = {}  # URL → 첫 등장 라인
    current_section_line = 0
    current_section_has_links = False

    for i, line in enumerate(lines):
        line_num = i + 1
        stripped = line.strip()

        # 빈 줄 스킵
        if not stripped:
            continue

        # 메인 제목 확인
        if _MAIN_TITLE_RE.match(stripped):
            if has_main_title:
                issues.append(ValidationIssue(
                    line=line_num, severity='warning',
                    message='메인 제목(#)이 여러 개 존재합니다.',
                ))
            has_main_title = True
            continue

        # 섹션 헤더 확인
        section_match = _SECTION_HEADER_RE.match(stripped)
        if section_match:
            # 이전 섹션이 비어있으면 경고
            if has_section and not current_section_has_links:
                issues.append(ValidationIssue(
                    line=current_section_line, severity='warning',
                    message='빈 섹션입니다. 링크가 없습니다.',
                ))
            has_section = True
            current_section_line = line_num
            current_section_has_links = False
            continue

        # 블록인용문 확인 (형식 오류 아님)
        if _BLOCKQUOTE_RE.match(stripped):
            continue

        # 링크 라인 확인
        if stripped.startswith('- '):
            link_match = _LINK_LINE_RE.match(stripped)
            if link_match:
                has_links = True
                current_section_has_links = True
                title = link_match.group(1)
                url = link_match.group(2)

                # 제목 비어있으면 에러
                if not title.strip():
                    issues.append(ValidationIssue(
                        line=line_num, severity='error',
                        message='링크 제목이 비어있습니다.',
                    ))

                # URL 형식 검증
                if not _URL_PATTERN.match(url):
                    issues.append(ValidationIssue(
                        line=line_num, severity='error',
                        message=f'잘못된 URL 형식: {url}',
                    ))

                # 중복 URL 감지
                if url in seen_urls:
                    issues.append(ValidationIssue(
                        line=line_num, severity='warning',
                        message=f'중복 URL: {url} (첫 등장: {seen_urls[url]}번째 줄)',
                    ))
                else:
                    seen_urls[url] = line_num
            else:
                # 리스트 항목이지만 링크 형식이 아님
                issues.append(ValidationIssue(
                    line=line_num, severity='warning',
                    message='리스트 항목이 올바른 링크 형식이 아닙니다. 형식: - [제목](URL): 설명',
                ))
            continue

        # 그 외: 인식할 수 없는 라인 (일반 텍스트는 경고하지 않음)

    # 마지막 섹션이 비어있는지 확인
    if has_section and not current_section_has_links:
        issues.append(ValidationIssue(
            line=current_section_line, severity='warning',
            message='빈 섹션입니다. 링크가 없습니다.',
        ))

    # 전체 구조 검증
    if not has_main_title:
        issues.append(ValidationIssue(
            line=0, severity='error',
            message='메인 제목(# )이 없습니다. llms.txt는 "# 사이트명"으로 시작해야 합니다.',
        ))

    if not has_section:
        issues.append(ValidationIssue(
            line=0, severity='warning',
            message='섹션 헤더(## )가 없습니다. 콘텐츠를 섹션으로 구분하는 것을 권장합니다.',
        ))

    if not has_links:
        issues.append(ValidationIssue(
            line=0, severity='error',
            message='링크가 하나도 없습니다. 최소 하나의 페이지 링크가 필요합니다.',
        ))

    return issues


def _parse_pages(pages: list[dict]) -> list[PageMeta]:
    """딕셔너리 목록을 PageMeta 목록으로 변환합니다.

    Args:
        pages: 페이지 딕셔너리 목록

    Returns:
        PageMeta 목록

    Raises:
        ValueError: 필수 필드 누락 또는 잘못된 값
    """
    metas: list[PageMeta] = []

    for i, page in enumerate(pages):
        # 필수 필드 확인
        url = page.get('url', '').strip()
        title = page.get('title', '').strip()

        if not url:
            raise ValueError(f'pages[{i}]: url 필드가 비어있습니다.')
        if not title:
            raise ValueError(f'pages[{i}]: title 필드가 비어있습니다.')

        # URL 형식 확인
        if not _URL_PATTERN.match(url):
            raise ValueError(f'pages[{i}]: 잘못된 URL 형식: {url}')

        # content_type 확인
        content_type = page.get('content_type', 'article').strip().lower()
        if content_type not in VALID_CONTENT_TYPES:
            raise ValueError(
                f'pages[{i}]: 잘못된 content_type: {content_type}. '
                f'허용 값: {VALID_CONTENT_TYPES}'
            )

        description = page.get('description', '').strip()

        metas.append(PageMeta(
            url=url,
            title=title,
            description=description,
            content_type=content_type,
        ))

    return metas


def _group_by_content_type(pages: list[PageMeta]) -> dict[str, list[PageMeta]]:
    """PageMeta 목록을 content_type별로 그룹화합니다."""
    groups: dict[str, list[PageMeta]] = {}

    for page in pages:
        if page.content_type not in groups:
            groups[page.content_type] = []
        groups[page.content_type].append(page)

    return groups


def parse_llms_txt(content: str) -> dict:
    """llms.txt 파일을 파싱하여 구조화된 데이터로 변환합니다.

    Args:
        content: llms.txt 파일 내용

    Returns:
        파싱 결과 딕셔너리:
        {
            'title': str,
            'description': str,
            'sections': [{'name': str, 'links': [{'title': str, 'url': str, 'description': str}]}]
        }
    """
    if not content or not content.strip():
        return {'title': '', 'description': '', 'sections': []}

    lines = content.split('\n')
    result: dict = {'title': '', 'description': '', 'sections': []}
    current_section: dict | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # 메인 제목
        title_match = _MAIN_TITLE_RE.match(stripped)
        if title_match and not result['title']:
            result['title'] = title_match.group(1).strip()
            continue

        # 블록인용문 (사이트 설명)
        blockquote_match = _BLOCKQUOTE_RE.match(stripped)
        if blockquote_match and not result['description'] and not result['sections']:
            result['description'] = blockquote_match.group(1).strip()
            continue

        # 섹션 헤더
        section_match = _SECTION_HEADER_RE.match(stripped)
        if section_match:
            current_section = {'name': section_match.group(1).strip(), 'links': []}
            result['sections'].append(current_section)
            continue

        # 링크 라인
        link_match = _LINK_LINE_RE.match(stripped)
        if link_match:
            link = {
                'title': link_match.group(1).strip(),
                'url': link_match.group(2).strip(),
                'description': (link_match.group(3) or '').strip(),
            }
            if current_section is not None:
                current_section['links'].append(link)
            continue

    return result
