"""Custom style generation service tests."""

from services.content.style_generation_service import generate_custom_style


class _FakeContentApi:
    def __init__(
        self,
        *,
        is_youtube=True,
        video_id="v456",
        title="테스트 영상",
        transcript=None,
    ):
        self.is_youtube = is_youtube
        self.video_id = video_id
        self.title = title
        self.transcript = transcript if transcript is not None else {"text": "자막 내용"}

    def is_youtube_url(self, url):
        return self.is_youtube

    def get_video_id(self, url):
        return self.video_id

    def get_content_title(self, url):
        return self.title

    def get_transcript(self, video_id):
        return self.transcript


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


def test_generate_custom_style_rejects_missing_url():
    payload, status = generate_custom_style(
        {},
        content_api=_FakeContentApi(),
        ai_client=_FakeAiClient("{}"),
        default_model="default-model",
    )

    assert status == 400
    assert payload == {"error": "YouTube URL이 필요합니다."}


def test_generate_custom_style_returns_ai_json_with_title_and_transcript_prompt():
    ai = _FakeAiClient(
        '{"styleName": "기술 분석", "stylePrompt": "기술 분석 프롬프트", '
        '"description": "적합"}'
    )

    payload, status = generate_custom_style(
        {"url": "https://youtube.com/watch?v=v456", "model": "gemini/test"},
        content_api=_FakeContentApi(title="테스트 영상", transcript={"text": "자막 내용"}),
        ai_client=ai,
        default_model="default-model",
    )

    assert status == 200
    assert payload["styleName"] == "기술 분석"
    assert payload["title"] == "테스트 영상"
    assert ai.calls[0]["model"] == "gemini/test"
    assert "자막 미리보기: 자막 내용" in ai.calls[0]["prompt"]


def test_generate_custom_style_uses_empty_transcript_placeholder_on_error():
    ai = _FakeAiClient(
        '{"styleName": "요약", "stylePrompt": "요약 프롬프트", '
        '"description": "적합"}'
    )

    generate_custom_style(
        {"url": "https://youtube.com/watch?v=v456"},
        content_api=_FakeContentApi(transcript={"error": "missing"}),
        ai_client=ai,
        default_model="default-model",
    )

    assert "자막 미리보기: (자막 없음)" in ai.calls[0]["prompt"]


def test_generate_custom_style_returns_500_when_ai_has_no_json():
    payload, status = generate_custom_style(
        {"url": "https://youtube.com/watch?v=v456"},
        content_api=_FakeContentApi(title="테스트 영상"),
        ai_client=_FakeAiClient("프롬프트 생성 결과입니다"),
        default_model="default-model",
    )

    assert status == 500
    assert payload == {"error": "AI 응답을 파싱할 수 없습니다.", "title": "테스트 영상"}


def test_generate_custom_style_returns_500_when_ai_json_is_invalid():
    payload, status = generate_custom_style(
        {"url": "https://youtube.com/watch?v=v456"},
        content_api=_FakeContentApi(title="테스트 영상"),
        ai_client=_FakeAiClient('{"styleName": "bad",}'),
        default_model="default-model",
    )

    assert status == 500
    assert payload == {"error": "AI 응답 JSON 파싱 실패", "title": "테스트 영상"}
