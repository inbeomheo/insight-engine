"""공급자 원문 오류와 운영체제 경로를 사용자 응답에서 차단한다."""
import pytest
from flask import Flask

from services.core.ai_service import _convert_error_message
from utils.responses import sanitize_error_for_client


@pytest.mark.parametrize('path', ['/Users/example/private/a.pdf', '/private/tmp/a',
                                  '/var/app/a', '/Volumes/data/a', r'Z:\private\a'])
def test_error_filter_hides_local_paths(path):
    with Flask(__name__).app_context():
        assert path not in sanitize_error_for_client('[AI 오류] 읽을 수 없습니다: ' + path)


def test_unknown_provider_message_is_not_returned():
    secretish = 'unexpected upstream diagnostic 12345'
    assert secretish not in _convert_error_message(secretish)
