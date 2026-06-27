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


def _truthy_env(*names: str) -> bool:
    return any(_truthy(os.getenv(name)) for name in names)


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


def _resolve_upstream(root: Path) -> tuple[str | None, str | None]:
    try:
        result = _run(['git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'], cwd=root)
    except Exception as exc:
        return None, f'git upstream could not be resolved: {exc.__class__.__name__}'

    upstream = result.stdout.strip()
    if result.returncode != 0 or not upstream:
        return None, 'production cutover requires a configured upstream branch so release commits are remote-traceable'

    return upstream, None


def git_upstream_check(root: Path, *, required: bool) -> dict[str, Any]:
    if not required:
        return _check('skipped', 'git_upstream', 'upstream Git branch is not required')

    upstream, error = _resolve_upstream(root)
    if error:
        return _check('error', 'git_upstream', error)

    return _check('ok', 'git_upstream', 'Git upstream branch is configured', upstream=upstream)


def git_upstream_pushed_check(root: Path, *, required: bool) -> dict[str, Any]:
    if not required:
        return _check('skipped', 'git_upstream_pushed', 'pushed Git upstream state is not required')

    upstream, error = _resolve_upstream(root)
    if error:
        return _check('error', 'git_upstream_pushed', error)

    try:
        result = _run(['git', 'rev-list', '--left-right', '--count', 'HEAD...@{u}'], cwd=root)
    except Exception as exc:
        return _check('error', 'git_upstream_pushed', f'git upstream comparison failed: {exc.__class__.__name__}')

    if result.returncode != 0:
        return _check('error', 'git_upstream_pushed', 'git upstream comparison failed', upstream=upstream)

    parts = result.stdout.split()
    try:
        ahead, behind = int(parts[0]), int(parts[1])
    except (IndexError, ValueError):
        return _check(
            'error',
            'git_upstream_pushed',
            'git upstream comparison returned an unexpected result',
            upstream=upstream,
            raw_output=result.stdout.strip(),
        )

    if ahead > 0:
        return _check(
            'error',
            'git_upstream_pushed',
            'production cutover requires HEAD to be pushed to its upstream branch',
            upstream=upstream,
            ahead=ahead,
            behind=behind,
        )

    return _check(
        'ok',
        'git_upstream_pushed',
        'Git HEAD is present on upstream branch',
        upstream=upstream,
        ahead=ahead,
        behind=behind,
    )


def run_checks(*, root: Path = ROOT, require_clean: bool, require_pushed: bool = False) -> dict[str, Any]:
    source_required = require_clean or require_pushed
    checks = [
        git_repo_check(root, required=source_required),
        git_head_check(root, required=source_required),
        git_worktree_clean_check(root, required=require_clean),
        git_upstream_check(root, required=require_pushed),
        git_upstream_pushed_check(root, required=require_pushed),
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
    parser.add_argument(
        '--require-pushed',
        action='store_true',
        default=_truthy_env('RELEASE_REQUIRE_PUSHED', 'RELEASE_REQUIRE_PUSHED_GIT'),
        help='Fail when HEAD has no upstream branch or contains commits not pushed to that upstream.',
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    report = run_checks(root=Path(args.root), require_clean=args.require_clean, require_pushed=args.require_pushed)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'ok' else 2


if __name__ == '__main__':
    raise SystemExit(main())
