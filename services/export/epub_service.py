"""
EPUB 전자책 내보내기 서비스

표준 라이브러리(zipfile + xml.etree)만 사용하여 EPUB 3.0 파일을 생성합니다.
"""
import io
import uuid
import zipfile
from datetime import datetime, timezone

import markdown


def create_epub(title: str, content: str, author: str = "") -> bytes:
    """마크다운 콘텐츠를 EPUB 파일로 변환합니다.

    Args:
        title: 책 제목
        content: 마크다운 본문
        author: 저자명 (선택)

    Returns:
        EPUB 파일의 바이트 데이터
    """
    book_id = str(uuid.uuid4())
    html_body = markdown.markdown(content, extensions=['tables', 'fenced_code'])
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # mimetype은 압축 없이 첫 번째로 (EPUB 규격)
        zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)

        # META-INF/container.xml
        zf.writestr('META-INF/container.xml', _container_xml())

        # content.opf (패키지 메타데이터)
        zf.writestr('OEBPS/content.opf', _content_opf(book_id, title, author, now))

        # toc.ncx (목차)
        zf.writestr('OEBPS/toc.ncx', _toc_ncx(book_id, title))

        # 본문 XHTML
        zf.writestr('OEBPS/chapter.xhtml', _chapter_xhtml(title, html_body))

        # 스타일시트
        zf.writestr('OEBPS/style.css', _default_css())

    return buf.getvalue()


def _container_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''


def _content_opf(book_id: str, title: str, author: str, date: str) -> str:
    author_tag = f'<dc:creator>{_esc(author)}</dc:creator>' if author else ''
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:{book_id}</dc:identifier>
    <dc:title>{_esc(title)}</dc:title>
    {author_tag}
    <dc:language>ko</dc:language>
    <meta property="dcterms:modified">{date}</meta>
  </metadata>
  <manifest>
    <item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="css" href="style.css" media-type="text/css"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="chapter"/>
  </spine>
</package>'''


def _toc_ncx(book_id: str, title: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:{book_id}"/>
  </head>
  <docTitle><text>{_esc(title)}</text></docTitle>
  <navMap>
    <navPoint id="chapter" playOrder="1">
      <navLabel><text>{_esc(title)}</text></navLabel>
      <content src="chapter.xhtml"/>
    </navPoint>
  </navMap>
</ncx>'''


def _chapter_xhtml(title: str, html_body: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ko" lang="ko">
<head>
  <meta charset="utf-8"/>
  <title>{_esc(title)}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
  <h1>{_esc(title)}</h1>
  {html_body}
</body>
</html>'''


def _default_css() -> str:
    return '''body { font-family: serif; line-height: 1.6; margin: 1em; }
h1, h2, h3 { margin-top: 1.5em; }
code { font-family: monospace; background: #f4f4f4; padding: 2px 4px; }
pre { background: #f4f4f4; padding: 1em; overflow-x: auto; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ccc; padding: 0.5em; }
blockquote { border-left: 3px solid #ccc; margin-left: 0; padding-left: 1em; color: #666; }'''


def _esc(text: str) -> str:
    """XML 이스케이프"""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
