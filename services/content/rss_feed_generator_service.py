"""
RSS/Atom 피드 생성 서비스

콘텐츠 컬렉션을 RSS 2.0 또는 Atom 형식의 XML 피드로 변환합니다.
"""
import html
import logging
import re
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

_HEADING_PATTERN = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)


def generate_rss(contents: List[dict], feed_title: str = 'Insight Engine Feed',
                 feed_link: str = '', feed_description: str = '',
                 format_type: str = 'rss') -> dict:
    """콘텐츠 컬렉션으로 RSS/Atom XML을 생성합니다.

    Args:
        contents: [{'title': str, 'content': str, 'link': str(opt), 'date': str(opt), 'author': str(opt)}]
        feed_title: 피드 제목
        feed_link: 피드 URL
        feed_description: 피드 설명
        format_type: 'rss' 또는 'atom'

    Returns:
        {'xml': str, 'item_count': int, 'format': str}
    """
    if not contents:
        return {'xml': '', 'item_count': 0, 'format': format_type}

    if format_type == 'atom':
        xml = _build_atom(contents, feed_title, feed_link, feed_description)
    else:
        xml = _build_rss(contents, feed_title, feed_link, feed_description)

    return {
        'xml': xml,
        'item_count': len(contents),
        'format': format_type,
    }


def _build_rss(contents: List[dict], title: str, link: str, desc: str) -> str:
    """RSS 2.0 XML을 빌드합니다."""
    now = datetime.now(tz=__import__('datetime').timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
    safe_title = html.escape(title)
    safe_link = html.escape(link or '#')
    safe_desc = html.escape(desc or title)

    items = []
    for item in contents:
        item_title = html.escape(item.get('title', _extract_title(item.get('content', ''))))
        item_link = html.escape(item.get('link', '#'))
        item_desc = html.escape(_make_description(item.get('content', '')))
        item_date = item.get('date', now)
        item_author = html.escape(item.get('author', ''))

        author_tag = f'<author>{item_author}</author>' if item_author else ''
        items.append(f"""    <item>
      <title>{item_title}</title>
      <link>{item_link}</link>
      <description>{item_desc}</description>
      <pubDate>{item_date}</pubDate>
      {author_tag}
    </item>""")

    items_xml = '\n'.join(items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{safe_title}</title>
    <link>{safe_link}</link>
    <description>{safe_desc}</description>
    <lastBuildDate>{now}</lastBuildDate>
{items_xml}
  </channel>
</rss>"""


def _build_atom(contents: List[dict], title: str, link: str, desc: str) -> str:
    """Atom 1.0 XML을 빌드합니다."""
    now = datetime.now(tz=__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    safe_title = html.escape(title)
    safe_link = html.escape(link or '#')

    entries = []
    for i, item in enumerate(contents):
        entry_title = html.escape(item.get('title', _extract_title(item.get('content', ''))))
        entry_link = html.escape(item.get('link', '#'))
        entry_content = html.escape(_make_description(item.get('content', '')))
        entry_date = item.get('date', now)
        entry_id = html.escape(item.get('link', f'entry-{i}'))
        author = item.get('author', '')
        author_tag = f'<author><name>{html.escape(author)}</name></author>' if author else ''

        entries.append(f"""  <entry>
    <title>{entry_title}</title>
    <link href="{entry_link}"/>
    <id>{entry_id}</id>
    <updated>{entry_date}</updated>
    <content type="html">{entry_content}</content>
    {author_tag}
  </entry>""")

    entries_xml = '\n'.join(entries)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{safe_title}</title>
  <link href="{safe_link}"/>
  <updated>{now}</updated>
  <id>{safe_link}</id>
{entries_xml}
</feed>"""


def _extract_title(content: str) -> str:
    """콘텐츠에서 제목을 추출합니다."""
    match = _HEADING_PATTERN.search(content)
    return match.group(1).strip() if match else '제목 없음'


def _make_description(content: str, max_len: int = 300) -> str:
    """콘텐츠에서 설명을 생성합니다."""
    clean = re.sub(r'^#{1,6}\s+.*$', '', content, flags=re.MULTILINE)
    clean = re.sub(r'[*_`~\[\]!()]', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    if len(clean) > max_len:
        clean = clean[:max_len - 3] + '...'
    return clean
