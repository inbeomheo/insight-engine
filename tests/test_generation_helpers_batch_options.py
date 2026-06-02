"""배치 단일 URL 생성의 고급 옵션 전달 테스트."""

from app import create_app
from routes import generation_helpers as gh


def test_process_single_url_passes_detail_and_web_search(monkeypatch):
    app = create_app()
    captured = {}

    monkeypatch.setattr(gh.content_service, 'is_youtube_url', lambda url: True)
    monkeypatch.setattr(gh.content_service, 'get_video_id', lambda url: 'abc123')
    monkeypatch.setattr(gh.content_service, 'get_content_title', lambda url: '테스트 영상')
    monkeypatch.setattr(gh.content_service, 'truncate_text', lambda text, max_tokens: text)
    monkeypatch.setattr(gh, '_fetch_youtube_content', lambda video_id: ('자막', [], None, '원문', 'mock', []))
    monkeypatch.setattr(gh, '_build_combined_content', lambda transcript, comments: transcript)
    monkeypatch.setattr(gh, 'get_model_max_tokens', lambda model: 1000)

    def fake_create_content(content, model, style_prompt, **kwargs):
        captured.update(kwargs)
        return {'title': '결과', 'content': '본문', 'html': '<p>본문</p>'}, 'prompt'

    monkeypatch.setattr(gh.ai_service, 'create_content', fake_create_content)

    result = gh._process_single_url(
        app,
        'https://www.youtube.com/watch?v=abc123',
        'chatmock/gpt-5.5',
        'blog_seo',
        {},
        None,
        detail_level='deep',
        web_search=True,
    )

    assert result['success'] is True
    assert captured['detail_level'] == 'deep'
    assert captured['web_search'] is True

