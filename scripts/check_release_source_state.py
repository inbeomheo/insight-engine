"""Check source tree state for provenance-safe production releases."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _truthy(value: str | None) -> bool:
    return (value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _check(status: str, name: str, message: str, **extra: Any) -> dict[str, Any]:
    payload = {'name': name, 'status': status, 'message': message}
    payload.update(extra)
    return payload


def _run(command: list[str], *, cwd: Path = ROOT, timeout: float = 10.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def git_repo_check(root: Path, *, required: bool) -> dict[str, Any]:
    try:
        result = _run(['git', 'rev-parse', '--is-inside-work-tree'], cwd=root)
    except Exception as exc:
        status = 'error' if required else 'skipped'
        return _check(status, 'git_repository', f'git repository check failed: {exc.__class__.__name__}')

    if result.returncode != 0 or result.stdout.strip() != 'true':
        status = 'error' if required else 'skipped'
        return _check(status, 'git_repository', 'release source is not inside a Git worktree')

    return _check('ok', 'git_repository', 'release source is inside a Git worktree')


def git_head_check(root: Path, *, required: bool) -> dict[str, Any]:
    try:
        result = _run(['git', 'rev-parse', 'HEAD'], cwd=root)
    except Exception as exc:
        status = 'error' if required else 'skipped'
        return _check(status, 'git_head', f'git HEAD could not be resolved: {exc.__class__.__name__}')

    sha = result.stdout.strip()
    if result.returncode != 0 or not sha:
        status = 'error' if required else 'skipped'
        return _check(status, 'git_head', 'git HEAD could not be resolved')

    return _check('ok', 'git_head', 'git HEAD resolved', git_sha=sha)


def git_worktree_clean_check(root: Path, *, required: bool) -> dict[str, Any]:
    if not required:
        return _check('skipped', 'git_worktree_clean', 'clean Git worktree is not required')

    try:
        result = _run(['git', 'status', '--porcelain=v1', '--untracked-files=all'], cwd=root)
    except Exception as exc:
        return _check('error', 'git_worktree_clean', f'git status failed: {exc.__class__.__name__}')

    if result.returncode != 0:
        return _check('error', 'git_worktree_clean', 'git status failed')

    entries = [line for line in result.stdout.splitlines() if line.strip()]
    if entries:
        return _check(
            'error',
            'git_worktree_clean',
            'production cutover requires a clean Git worktree so image labels match committed source',
            dirty_count=len(entries),
            dirty_sample=entries[:25],
        )

    return _check('ok', 'git_worktree_clean', 'Git worktree is clean')


def run_checks(*, root: Path = ROOT, require_clean: bool) -> dict[str, Any]:
    checks = [
        git_repo_check(root, required=require_clean),
        git_head_check(root, required=require_clean),
        git_worktree_clean_check(root, required=require_clean),
    ]
    status = 'error' if any(check['status'] == 'error' for check in checks) else 'ok'
    return {
        'service': 'insight-engine',
        'status': status,
        'checks': checks,
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--root',
        default=os.getenv('RELEASE_SOURCE_ROOT') or str(ROOT),
        help='Git worktree root to inspect.',
    )
    parser.add_argument(
        '--require-clean',
        action='store_true',
        default=_truthy(os.getenv('RELEASE_REQUIRE_CLEAN_GIT')),
        help='Fail when tracked, staged, or untracked source changes are present.',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    report = run_checks(root=Path(args.root), require_clean=args.require_clean)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'ok' else 2


if __name__ == '__main__':
    raise SystemExit(main())
