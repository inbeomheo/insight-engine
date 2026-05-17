"""Style recommendation service tests."""

from services.content.style_recommendation_service import recommend_content_style


class _FakeContentApi:
    def __init__(self, *, is_youtube=True, video_id="v123", title="테스트 영상"):
        self.is_youtube = is_youtube
        self.video_id = video_id
        self.title = title

    def is_youtube_url(self, url):
        return self.is_youtube

    def get_video_id(self, url):
        return self.video_id

    def get_content_title(self, url):
        return self.title


class _FakeAiClient:
    def __init__(self, content):
        self.content = content
        self.calls = []

    def create_content(self, prompt, model, style_prompt=""):
        self.calls.append({
            "prompt": prompt,
            "model": model,
            "style_prompt": style_prompt,
        })
        return {"content": self.content}


def test_recommend_content_style_rejects_missing_url():
    payload, status = recommend_content_style(
        {},
        content_api=_FakeContentApi(),
        ai_client=_FakeAiClient("{}"),
        style_options=[],
        default_model="default-model",
    )

    assert status == 400
    assert payload == {"error": "YouTube URL이 필요합니다."}


def test_recommend_content_style_rejects_invalid_youtube_url():
    payload, status = recommend_content_style(
        {"url": "https://example.com"},
        content_api=_FakeContentApi(is_youtube=False),
        ai_client=_FakeAiClient("{}"),
        style_options=[],
        default_model="default-model",
    )

    assert status == 400
    assert payload == {"error": "유효한 YouTube URL을 입력해주세요."}


def test_recommend_content_style_returns_ai_json_with_title():
    ai = _FakeAiClient(
        '{"style": "blog_seo", "reason": "적합", '
        '"modifiers": {"length": "medium"}}'
    )

    payload, status = recommend_content_style(
        {"url": "https://youtube.com/watch?v=v123", "model": "gemini/test"},
        content_api=_FakeContentApi(title="테스트 영상"),
        ai_client=ai,
        style_options=[("blog_seo", "SEO 블로그")],
        default_model="default-model",
    )

    assert status == 200
    assert payload["style"] == "blog_seo"
    assert payload["title"] == "테스트 영상"
    assert ai.calls[0]["model"] == "gemini/test"
    assert "blog_seo(SEO 블로그)" in ai.calls[0]["prompt"]


def test_recommend_content_style_uses_default_when_ai_has_no_json():
    payload, status = recommend_content_style(
        {"url": "https://youtube.com/watch?v=v123"},
        content_api=_FakeContentApi(title="테스트 영상"),
        ai_client=_FakeAiClient("추천 스타일은 detailed입니다"),
        style_options=[],
        default_model="default-model",
    )

    assert status == 200
    assert payload == {
        "style": "detailed",
        "reason": "기본 추천",
        "modifiers": {"length": "medium", "tone": "professional", "emoji": "none"},
        "title": "테스트 영상",
    }


def test_recommend_content_style_uses_parse_failure_default_for_bad_json():
    payload, status = recommend_content_style(
        {"url": "https://youtube.com/watch?v=v123"},
        content_api=_FakeContentApi(title="테스트 영상"),
        ai_client=_FakeAiClient('{"style": "blog_seo"'),
        style_options=[],
        default_model="default-model",
    )

    assert status == 200
    assert payload["style"] == "detailed"
    assert payload["reason"] == "기본 추천"
