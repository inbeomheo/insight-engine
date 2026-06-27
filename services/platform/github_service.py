"""
GitHub README 추출 서비스

GitHub API를 사용하여 리포지토리의 README 파일을 추출합니다.
인증 없이 공개 리포지토리만 지원 (rate limit: 60 req/hr).
"""
from __future__ import annotations

import base64
import logging
import re
from typing import Dict

import requests

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 15  # 초
_GITHUB_API_BASE = "https://api.github.com"

# GitHub URL에서 owner/repo 추출
_GITHUB_REPO_RE = re.compile(
    r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)


def _fetch_readme_raw(owner: str, repo: str) -> str:
    """GitHub API로 README를 가져와 디코딩합니다.

    Raises:
        ValueError: API 오류, 디코딩 실패, 빈 README
    """
    api_url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
    try:
        resp = requests.get(
            api_url,
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=_REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        status_code = getattr(resp, "status_code", 0)
        if isinstance(status_code, int) and 300 <= status_code < 400:
            raise ValueError(f"GitHub API 리다이렉트 차단: {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise ValueError(f"README를 찾을 수 없습니다: {owner}/{repo}")
        raise ValueError(f"GitHub API 오류: {e}")
    except requests.RequestException as e:
        raise ValueError(f"GitHub에 연결할 수 없습니다: {e}")

    if data.get("encoding", "base64") != "base64":
        raise ValueError(f"지원하지 않는 인코딩: {data.get('encoding')}")

    try:
        content = base64.b64decode(data.get("content", "")).decode("utf-8")
    except Exception as e:
        raise ValueError(f"README 디코딩 실패: {e}")

    if not content.strip():
        raise ValueError(f"README가 비어 있습니다: {owner}/{repo}")
    return content


def extract_github_readme(url: str) -> Dict:
    """GitHub 리포지토리 URL에서 README를 추출합니다.

    Args:
        url: GitHub 리포지토리 URL (예: https://github.com/owner/repo)

    Returns:
        {"title": str, "content": str, "url": str, "source_type": "github"}

    Raises:
        ValueError: URL이 유효하지 않거나 README를 찾을 수 없는 경우
    """
    owner, repo = _parse_github_url(url)
    content = _fetch_readme_raw(owner, repo)

    meta = _get_repo_metadata(owner, repo)
    repo_desc = meta.get("description", "")
    header = f"리포지토리: {owner}/{repo}"
    if repo_desc:
        header += f"\n설명: {repo_desc}"

    return {
        "title": f"{owner}/{repo}",
        "content": f"{header}\n\n{content}",
        "url": url,
        "source_type": "github",
        "stars": meta.get("stars", 0),
        "forks": meta.get("forks", 0),
    }


def _parse_github_url(url: str) -> tuple:
    """GitHub URL에서 owner와 repo를 추출합니다.

    Returns:
        (owner, repo) 튜플

    Raises:
        ValueError: 유효하지 않은 GitHub URL
    """
    match = _GITHUB_REPO_RE.search(url)
    if not match:
        raise ValueError(f"유효하지 않은 GitHub URL: {url}")

    owner = match.group(1)
    repo = match.group(2)

    # .git 접미사 제거
    if repo.endswith(".git"):
        repo = repo[:-4]

    return owner, repo


def _get_repo_metadata(owner: str, repo: str) -> Dict:
    """리포지토리 메타데이터를 가져옵니다 (실패 시 빈 dict).

    Returns:
        {"description": str, "stars": int, "forks": int}
    """
    try:
        resp = requests.get(
            f"{_GITHUB_API_BASE}/repos/{owner}/{repo}",
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=_REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        status_code = getattr(resp, "status_code", 0)
        if isinstance(status_code, int) and 300 <= status_code < 400:
            return {"description": "", "stars": 0, "forks": 0}
        resp.raise_for_status()
        data = resp.json()
        return {
            "description": data.get("description", "") or "",
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
        }
    except Exception:
        return {"description": "", "stars": 0, "forks": 0}
