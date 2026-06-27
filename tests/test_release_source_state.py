"""Release source state checks for provenance-safe cutovers."""
from pathlib import Path
from unittest.mock import patch

from scripts import check_release_source_state


class _Completed:
    def __init__(self, returncode=0, stdout=''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ''


def test_release_source_state_allows_dirty_worktree_when_not_required(tmp_path):
    def fake_run(command, **_kwargs):
        if command[:2] == ['git', 'rev-parse'] and command[2] == '--is-inside-work-tree':
            return _Completed(stdout='true\n')
        if command[:2] == ['git', 'rev-parse'] and command[2] == 'HEAD':
            return _Completed(stdout='abcdef1234567890abcdef1234567890abcdef12\n')
        if command[:2] == ['git', 'status']:
            return _Completed(stdout=' M app.py\n?? scratch.txt\n')
        return _Completed(returncode=1)

    with patch.object(check_release_source_state, '_run', side_effect=fake_run):
        report = check_release_source_state.run_checks(root=tmp_path, require_clean=False)

    clean = next(check for check in report['checks'] if check['name'] == 'git_worktree_clean')
    assert report['status'] == 'ok'
    assert clean['status'] == 'skipped'


def test_release_source_state_rejects_dirty_worktree_when_required(tmp_path):
    def fake_run(command, **_kwargs):
        if command[:2] == ['git', 'rev-parse'] and command[2] == '--is-inside-work-tree':
            return _Completed(stdout='true\n')
        if command[:2] == ['git', 'rev-parse'] and command[2] == 'HEAD':
            return _Completed(stdout='abcdef1234567890abcdef1234567890abcdef12\n')
        if command[:2] == ['git', 'status']:
            return _Completed(stdout=' M app.py\nA  scripts/release.py\n?? scratch.txt\n')
        return _Completed(returncode=1)

    with patch.object(check_release_source_state, '_run', side_effect=fake_run):
        report = check_release_source_state.run_checks(root=tmp_path, require_clean=True)

    clean = next(check for check in report['checks'] if check['name'] == 'git_worktree_clean')
    assert report['status'] == 'error'
    assert clean['status'] == 'error'
    assert clean['dirty_count'] == 3
    assert ' M app.py' in clean['dirty_sample']


def test_release_source_state_accepts_clean_worktree_when_required(tmp_path):
    def fake_run(command, **_kwargs):
        if command[:2] == ['git', 'rev-parse'] and command[2] == '--is-inside-work-tree':
            return _Completed(stdout='true\n')
        if command[:2] == ['git', 'rev-parse'] and command[2] == 'HEAD':
            return _Completed(stdout='abcdef1234567890abcdef1234567890abcdef12\n')
        if command[:2] == ['git', 'status']:
            return _Completed(stdout='')
        return _Completed(returncode=1)

    with patch.object(check_release_source_state, '_run', side_effect=fake_run):
        report = check_release_source_state.run_checks(root=tmp_path, require_clean=True)

    assert report['status'] == 'ok'
    assert any(check['name'] == 'git_head' and check['git_sha'].startswith('abcdef') for check in report['checks'])


def test_release_source_state_rejects_non_git_root_when_required(tmp_path):
    with patch.object(check_release_source_state, '_run', return_value=_Completed(returncode=1)):
        report = check_release_source_state.run_checks(root=Path('/not-a-repo'), require_clean=True)

    assert report['status'] == 'error'
    assert any(check['name'] == 'git_repository' and check['status'] == 'error' for check in report['checks'])
