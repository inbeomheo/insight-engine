"""
콘텐츠 변경 로그(Changelog) 생성 서비스

콘텐츠 수정 이력을 사람이 읽을 수 있는 변경 로그로 변환합니다.
content_diff_service의 결과를 입력으로 받아 가독성 높은 요약을 생성.
"""
import logging
import re
from datetime import datetime, timezone
from typing import List

logger = logging.getLogger(__name__)


def generate_changelog(entries: List[dict], title: str = '변경 이력') -> dict:
    """변경 이력 엔트리들로 변경 로그를 생성합니다.

    Args:
        entries: [{'version': str, 'date': str, 'changes': [str], 'author': str(opt)}]
                 또는 diff 결과: [{'version': str, 'date': str, 'diff_stats': dict}]
        title: 변경 로그 제목

    Returns:
        {
            'changelog_md': str,
            'changelog_text': str,
            'total_entries': int,
            'total_changes': int,
        }
    """
    if not entries:
        return {'changelog_md': '', 'changelog_text': '', 'total_entries': 0, 'total_changes': 0}

    md_lines = [f'# {title}', '']
    text_lines = [title, '=' * len(title), '']
    total_changes = 0

    for entry in entries:
        version = entry.get('version', '')
        date = entry.get('date', _now_iso())
        author = entry.get('author', '')
        changes = entry.get('changes', [])
        diff_stats = entry.get('diff_stats', None)

        # 버전 헤더
        header_parts = []
        if version:
            header_parts.append(version)
        header_parts.append(f'({date})')
        if author:
            header_parts.append(f'— {author}')
        header = ' '.join(header_parts)

        md_lines.append(f'## {header}')
        text_lines.append(header)
        text_lines.append('-' * len(header))

        # 변경사항 목록 (문자열이면 리스트로 변환)
        if isinstance(changes, str):
            changes = [changes]
        if changes:
            for change in changes:
                change_str = str(change) if not isinstance(change, str) else change
                categorized = _categorize_change(change_str)
                md_lines.append(f'- {categorized}')
                text_lines.append(f'  • {categorized}')
                total_changes += 1
        elif diff_stats:
            # diff_stats에서 변경 요약 자동 생성
            auto_changes = _summarize_diff_stats(diff_stats)
            for change in auto_changes:
                if change != '변경사항 없음':
                    md_lines.append(f'- {change}')
                    text_lines.append(f'  • {change}')
                    total_changes += 1

        md_lines.append('')
        text_lines.append('')

    changelog_md = '\n'.join(md_lines).strip()
    changelog_text = '\n'.join(text_lines).strip()

    return {
        'changelog_md': changelog_md,
        'changelog_text': changelog_text,
        'total_entries': len(entries),
        'total_changes': total_changes,
    }


def _categorize_change(change: str) -> str:
    """변경사항에 카테고리 접두사를 추가합니다."""
    lower = change.lower()
    if any(kw in lower for kw in ['추가', 'add', '신규', '생성']):
        return f'**추가**: {change}'
    elif any(kw in lower for kw in ['수정', 'fix', '변경', '개선', 'update']):
        return f'**수정**: {change}'
    elif any(kw in lower for kw in ['삭제', 'remove', '제거']):
        return f'**삭제**: {change}'
    elif any(kw in lower for kw in ['리팩토링', 'refactor', '구조']):
        return f'**리팩토링**: {change}'
    return change


def _summarize_diff_stats(stats: dict) -> List[str]:
    """diff 통계에서 변경 요약을 자동 생성합니다."""
    summaries = []
    additions = stats.get('additions', 0)
    deletions = stats.get('deletions', 0)
    modifications = stats.get('modifications', 0)

    if additions > 0:
        summaries.append(f'{additions}개 줄 추가')
    if deletions > 0:
        summaries.append(f'{deletions}개 줄 삭제')
    if modifications > 0:
        summaries.append(f'{modifications}개 줄 수정')

    return summaries if summaries else ['변경사항 없음']


def _now_iso() -> str:
    """현재 시간을 ISO 형식으로 반환합니다."""
    return datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')
