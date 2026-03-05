"""
타임라인 인포그래픽 서비스

이벤트 목록을 시각적 타임라인 HTML로 변환합니다.
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def generate_timeline(events: List[Dict[str, str]]) -> str:
    """이벤트 목록을 시각적 타임라인 HTML로 변환합니다.

    Args:
        events: [{"date": "2024-01", "title": "...", "description": "..."}, ...]

    Returns:
        독립 실행 가능한 타임라인 HTML 문자열

    Raises:
        ValueError: events가 비어 있거나 형식 오류
    """
    if not events:
        raise ValueError('타임라인 이벤트 목록이 비어 있습니다.')

    for i, ev in enumerate(events):
        if 'title' not in ev:
            raise ValueError(f'이벤트 {i+1}에 title 필드가 필요합니다.')

    items_html = []
    for i, ev in enumerate(events):
        date = ev.get('date', '')
        title = ev.get('title', '')
        desc = ev.get('description', '')
        side = 'left' if i % 2 == 0 else 'right'

        items_html.append(f"""
    <div class="tl-item tl-{side}">
      <div class="tl-dot"></div>
      <div class="tl-content">
        {f'<span class="tl-date">{date}</span>' if date else ''}
        <h3 class="tl-title">{title}</h3>
        {f'<p class="tl-desc">{desc}</p>' if desc else ''}
      </div>
    </div>""")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Timeline</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;background:#f8fafc;padding:40px 20px}}
.tl-container{{position:relative;max-width:700px;margin:0 auto}}
.tl-container::before{{content:'';position:absolute;left:50%;top:0;bottom:0;width:2px;background:#cbd5e1;transform:translateX(-50%)}}
.tl-item{{position:relative;width:50%;padding:12px 30px;margin-bottom:24px}}
.tl-left{{left:0;text-align:right}}
.tl-right{{left:50%;text-align:left}}
.tl-dot{{position:absolute;top:16px;width:14px;height:14px;border-radius:50%;background:#2563eb;border:3px solid #fff;box-shadow:0 0 0 2px #2563eb}}
.tl-left .tl-dot{{right:-7px}}
.tl-right .tl-dot{{left:-7px}}
.tl-content{{background:#fff;padding:16px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
.tl-date{{font-size:12px;color:#6b7280;font-weight:500}}
.tl-title{{font-size:15px;font-weight:600;color:#1e293b;margin:4px 0}}
.tl-desc{{font-size:13px;color:#475569;line-height:1.5;margin-top:4px}}
@media(max-width:600px){{
  .tl-container::before{{left:20px}}
  .tl-item{{width:100%;left:0!important;text-align:left!important;padding-left:44px;padding-right:12px}}
  .tl-left .tl-dot,.tl-right .tl-dot{{left:13px!important;right:auto!important}}
}}
</style>
</head>
<body>
<div class="tl-container">
{''.join(items_html)}
</div>
</body>
</html>"""
