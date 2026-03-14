"""
Interactive HTML 보고서 서비스

마크다운 콘텐츠를 목차(자동 생성) + 섹션 접기 + 텍스트 검색이 포함된
독립 HTML 파일로 변환합니다.
"""
import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


def _extract_headings(content: str) -> List[Tuple[int, str, str]]:
    """마크다운에서 헤딩을 추출합니다.

    Returns:
        [(level, id, text), ...]
    """
    headings = []
    for match in re.finditer(r'^(#{1,3})\s+(.+)$', content, re.MULTILINE):
        level = len(match.group(1))
        text = match.group(2).strip()
        heading_id = re.sub(r'[^\w가-힣-]', '', text.lower().replace(' ', '-'))[:40]
        heading_id = heading_id or f'section-{len(headings)}'
        headings.append((level, heading_id, text))
    return headings


def _build_toc(headings: List[Tuple[int, str, str]]) -> str:
    """목차 HTML을 생성합니다."""
    if not headings:
        return ''
    items = []
    for level, hid, text in headings:
        indent = (level - 1) * 16
        items.append(
            f'<a href="#{hid}" class="toc-link" style="padding-left:{indent}px;">{text}</a>'
        )
    return '\n'.join(items)


def _md_to_sections(content: str, headings: List[Tuple[int, str, str]]) -> str:
    """마크다운을 접기 가능한 섹션 HTML로 변환합니다."""
    lines = content.split('\n')
    sections = []
    current_body = []
    current_heading = None

    def flush() -> None:
        nonlocal current_heading
        body = '\n'.join(current_body).strip()
        if current_heading:
            _, hid, text = current_heading
            body_html = _simple_md_to_html(body)
            sections.append(
                f'<details class="section" open>'
                f'<summary id="{hid}">{text}</summary>'
                f'<div class="section-body">{body_html}</div>'
                f'</details>'
            )
        elif body:
            sections.append(f'<div class="section-body">{_simple_md_to_html(body)}</div>')
        current_body.clear()
        current_heading = None

    heading_idx = 0
    for line in lines:
        stripped = line.strip()
        heading_match = re.match(r'^(#{1,3})\s+(.+)$', stripped)
        if heading_match and heading_idx < len(headings):
            flush()
            current_heading = headings[heading_idx]
            heading_idx += 1
        else:
            current_body.append(line)

    flush()
    return '\n'.join(sections)


def _simple_md_to_html(text: str) -> str:
    """간단한 마크다운 → HTML 변환."""
    # 볼드, 이탤릭
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # 인라인 코드
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # 링크
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    # 비순서 목록
    text = re.sub(r'^[-*+]\s+(.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    # 순서 목록
    text = re.sub(r'^\d+\.\s+(.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    # 수평선
    text = re.sub(r'^---+$', '<hr/>', text, flags=re.MULTILINE)
    # 빈 줄 → <br>
    text = re.sub(r'\n\n+', '<br/><br/>', text)
    text = re.sub(r'\n', '<br/>', text)
    return text


def generate_interactive_report(content: str, title: str = '보고서') -> str:
    """마크다운 콘텐츠를 인터랙티브 HTML 보고서로 변환합니다.

    Args:
        content: 마크다운 콘텐츠
        title: 보고서 제목

    Returns:
        독립 HTML 문자열 (목차 + 접기 + 검색)

    Raises:
        ValueError: 콘텐츠가 비어 있음
    """
    if not content or not content.strip():
        raise ValueError('보고서로 변환할 콘텐츠가 필요합니다.')

    headings = _extract_headings(content)
    toc_html = _build_toc(headings)
    sections_html = _md_to_sections(content, headings)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;background:#f8fafc;color:#1e293b;line-height:1.7}}
.wrapper{{display:flex;max-width:1000px;margin:0 auto;padding:24px 16px;gap:24px}}
.sidebar{{width:220px;position:sticky;top:24px;align-self:flex-start;flex-shrink:0}}
.main{{flex:1;min-width:0}}
.search-box{{width:100%;padding:8px 12px;border:1px solid #e2e8f0;border-radius:6px;font-size:14px;margin-bottom:16px}}
.search-box:focus{{outline:none;border-color:#2563eb;box-shadow:0 0 0 2px rgba(37,99,235,.15)}}
.toc{{background:#fff;border-radius:8px;padding:12px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.toc-link{{display:block;padding:4px 8px;font-size:13px;color:#475569;text-decoration:none;border-radius:4px}}
.toc-link:hover{{background:#f1f5f9;color:#1e293b}}
.section{{background:#fff;border-radius:8px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.section>summary{{padding:14px 18px;font-size:16px;font-weight:600;cursor:pointer;list-style:none;display:flex;align-items:center;gap:8px}}
.section>summary::before{{content:'\\25BC';font-size:10px;color:#94a3b8;transition:transform .2s}}
.section[open]>summary::before{{transform:rotate(0)}}
.section:not([open])>summary::before{{transform:rotate(-90deg)}}
.section-body{{padding:0 18px 16px;font-size:14px}}
.section-body code{{background:#f1f5f9;padding:2px 5px;border-radius:3px;font-size:13px}}
.section-body a{{color:#2563eb}}
.section-body li{{margin:4px 0}}
mark{{background:#fef08a;padding:0 2px;border-radius:2px}}
hr{{border:0;border-top:1px solid #e2e8f0;margin:12px 0}}
@media(max-width:700px){{
  .wrapper{{flex-direction:column}}
  .sidebar{{width:100%;position:static}}
}}
</style>
</head>
<body>
<div class="wrapper">
  <aside class="sidebar">
    <input type="text" class="search-box" placeholder="검색..." id="searchInput"/>
    <nav class="toc">
      {toc_html}
    </nav>
  </aside>
  <main class="main">
    <h1 style="font-size:24px;font-weight:700;margin-bottom:20px;">{title}</h1>
    {sections_html}
  </main>
</div>
<script>
(function(){{
  var input=document.getElementById('searchInput');
  input.addEventListener('input',function(){{
    var q=this.value.trim().toLowerCase();
    var sections=document.querySelectorAll('.section, .section-body');
    if(!q){{
      document.querySelectorAll('mark').forEach(function(m){{
        m.replaceWith(m.textContent);
      }});
      sections.forEach(function(s){{s.style.display=''}});
      return;
    }}
    // 리셋
    document.querySelectorAll('mark').forEach(function(m){{m.replaceWith(m.textContent)}});
    document.querySelectorAll('.section').forEach(function(s){{
      var text=s.textContent.toLowerCase();
      if(text.indexOf(q)!==-1){{
        s.style.display='';
        s.open=true;
        // 하이라이트
        var body=s.querySelector('.section-body');
        if(body){{
          body.innerHTML=body.innerHTML.replace(
            new RegExp('('+q.replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&')+')','gi'),
            '<mark>$1</mark>'
          );
        }}
      }}else{{
        s.style.display='none';
      }}
    }});
  }});
}})();
</script>
</body>
</html>"""
