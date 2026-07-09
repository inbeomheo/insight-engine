"""Markdown 내보내기 서비스."""
from __future__ import annotations

import io
import re


def export_markdown(
    title: str,
    content: str,
    frontmatter: dict | None = None,
    metadata: dict | None = None,
    include_separator: bool = False,
) -> io.BytesIO:
    """마크다운 파일을 BytesIO로 반환합니다.

    Args:
        title: 문서 제목
        content: 마크다운 본문
        frontmatter: YAML frontmatter 딕셔너리 (title, date, tags 등)
        metadata: 생성 메타데이터 (model, style, generated_at 등).
                  포함 시 문서 하단에 메타 정보 섹션이 추가됨.
        include_separator: True이면 ## 헤딩 사이에 수평 구분선(---) 삽입.
    """
    parts = []
    if frontmatter:
        parts.append('---')
        for key, value in frontmatter.items():
            if isinstance(value, list):
                parts.append(f'{key}:')
                for item in value:
                    parts.append(f'  - {item}')
            else:
                parts.append(f'{key}: {value}')
        parts.append('---')
        parts.append('')

    body = content
    if include_separator:
        body = re.sub(r'\n(## )', r'\n---\n\n\1', body)

    parts.append(f"# {title}\n\n{body}")

    if metadata:
        meta_lines = ['\n---\n', '## 생성 정보\n']
        for key, value in metadata.items():
            meta_lines.append(f'- **{key}**: {value}')
        parts.append('\n'.join(meta_lines))

    text = '\n'.join(parts)
    return io.BytesIO(text.encode('utf-8'))
