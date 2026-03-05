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

    # README 가져오기
    api_url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
    try:
        resp = requests.get(
            api_url,
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            raise ValueError(f"README를 찾을 수 없습니다: {owner}/{repo}")
        raise ValueError(f"GitHub API 오류: {e}")
    except requests.RequestException as e:
        raise ValueError(f"GitHub에 연결할 수 없습니다: {e}")

    # base64 디코드
    content_b64 = data.get("content", "")
    encoding = data.get("encoding", "base64")

    if encoding != "base64":
        raise ValueError(f"지원하지 않는 인코딩: {encoding}")

    try:
        content = base64.b64decode(content_b64).decode("utf-8")
    except Exception as e:
        raise ValueError(f"README 디코딩 실패: {e}")

    if not content.strip():
        raise ValueError(f"README가 비어 있습니다: {owner}/{repo}")

    # 리포지토리 정보를 제목에 포함
    title = f"{owner}/{repo}"

    # 리포지토리 설명 가져오기 (선택적)
    repo_desc = _get_repo_description(owner, repo)
    if repo_desc:
        content = f"리포지토리: {owner}/{repo}\n설명: {repo_desc}\n\n{content}"
    else:
        content = f"리포지토리: {owner}/{repo}\n\n{content}"

    return {
        "title": title,
        "content": content,
        "url": url,
        "source_type": "github",
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


def _get_repo_description(owner: str, repo: str) -> str:
    """리포지토리 설명을 가져옵니다 (실패 시 빈 문자열)."""
    try:
        resp = requests.get(
            f"{_GITHUB_API_BASE}/repos/{owner}/{repo}",
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("description", "") or ""
    except Exception:
        return ""
