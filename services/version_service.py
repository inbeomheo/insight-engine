"""버전 히스토리 서비스 (F5-04)

콘텐츠의 버전 저장, 비교, 복원 기능을 제공합니다.
인메모리 저장소 기반 — Supabase 연동 시 DB 교체 가능.
"""
import uuid
import time
import difflib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 인메모리 버전 저장소: {content_id: [version, ...]}
_versions: dict[str, list[dict]] = {}

# 콘텐츠당 최대 버전 수
MAX_VERSIONS_PER_CONTENT = 50


def save_version(content_id: str, title: str, content: str, html: str = '',
                 author_id: str = '', note: str = '') -> dict:
    """콘텐츠의 새 버전을 저장합니다."""
    if content_id not in _versions:
        _versions[content_id] = []

    versions = _versions[content_id]
    version_number = len(versions) + 1

    version = {
        'id': str(uuid.uuid4()),
        'content_id': content_id,
        'version': version_number,
        'title': title,
        'content': content,
        'html': html,
        'author_id': author_id,
        'note': note,
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }

    versions.append(version)

    # 최대 버전 수 초과 시 오래된 것 제거
    if len(versions) > MAX_VERSIONS_PER_CONTENT:
        _versions[content_id] = versions[-MAX_VERSIONS_PER_CONTENT:]

    logger.info("버전 저장: content_id=%s, v%d", content_id, version_number)
    return version


def list_versions(content_id: str) -> list[dict]:
    """콘텐츠의 모든 버전 목록을 반환합니다 (메타데이터만, content 제외)."""
    versions = _versions.get(content_id, [])
    return [
        {k: v for k, v in ver.items() if k not in ('content', 'html')}
        for ver in reversed(versions)  # 최신순
    ]


def get_version(content_id: str, version_id: str) -> Optional[dict]:
    """특정 버전의 전체 데이터를 반환합니다."""
    for ver in _versions.get(content_id, []):
        if ver['id'] == version_id:
            return ver
    return None


def diff_versions(content_id: str, version_id_a: str, version_id_b: str) -> Optional[dict]:
    """두 버전의 차이를 unified diff로 반환합니다."""
    ver_a = get_version(content_id, version_id_a)
    ver_b = get_version(content_id, version_id_b)
    if not ver_a or not ver_b:
        return None

    lines_a = ver_a['content'].splitlines(keepends=True)
    lines_b = ver_b['content'].splitlines(keepends=True)
    diff = list(difflib.unified_diff(
        lines_a, lines_b,
        fromfile=f"v{ver_a['version']}",
        tofile=f"v{ver_b['version']}",
    ))

    return {
        'version_a': ver_a['version'],
        'version_b': ver_b['version'],
        'diff': ''.join(diff),
        'additions': sum(1 for l in diff if l.startswith('+') and not l.startswith('+++')),
        'deletions': sum(1 for l in diff if l.startswith('-') and not l.startswith('---')),
    }


def restore_version(content_id: str, version_id: str) -> Optional[dict]:
    """특정 버전을 복원하여 새 버전으로 저장합니다."""
    ver = get_version(content_id, version_id)
    if not ver:
        return None

    return save_version(
        content_id=content_id,
        title=ver['title'],
        content=ver['content'],
        html=ver.get('html', ''),
        author_id=ver.get('author_id', ''),
        note=f"v{ver['version']}에서 복원됨",
    )
