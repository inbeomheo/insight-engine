"""sanitize_path 경로 순회 방어 유틸리티 테스트"""
import os
import pytest

from utils.responses import sanitize_path


class TestSanitizePath:
    """sanitize_path 유틸리티 함수 테스트"""

    def test_normal_relative_path(self):
        """정상 상대 경로는 허용"""
        result = sanitize_path('finetune', './data')
        assert result.endswith(os.path.join('data', 'finetune'))

    def test_normal_subdir(self):
        """하위 디렉토리 경로는 허용"""
        result = sanitize_path('output/v2', './data')
        assert result.endswith(os.path.join('data', 'output', 'v2'))

    def test_dot_dot_traversal_blocked(self):
        """../ 경로 순회 시도는 차단"""
        with pytest.raises(ValueError, match='허용 범위'):
            sanitize_path('../../etc/passwd', './data')

    def test_absolute_path_outside_blocked(self):
        """허용 범위 밖의 절대 경로는 차단"""
        with pytest.raises(ValueError, match='허용 범위'):
            sanitize_path('/etc/passwd', './data')

    def test_dot_dot_in_middle_blocked(self):
        """중간에 ../가 포함된 경로 탈출 시도 차단"""
        with pytest.raises(ValueError, match='허용 범위'):
            sanitize_path('subdir/../../outside', './data')

    def test_same_as_base_allowed(self):
        """기본 디렉토리 자체 경로는 허용"""
        result = sanitize_path('.', './data')
        base = os.path.realpath(os.path.abspath('./data'))
        assert result == base

    def test_sibling_directory_blocked(self):
        """형제 디렉토리(접두사만 일치)는 차단"""
        with pytest.raises(ValueError, match='허용 범위'):
            sanitize_path('../data2', './data')

    def test_empty_path_resolves_to_base(self):
        """빈 경로는 기본 디렉토리로 해석"""
        result = sanitize_path('', './data')
        base = os.path.realpath(os.path.abspath('./data'))
        assert result == base
