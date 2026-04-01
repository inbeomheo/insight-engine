import sys
from types import ModuleType, SimpleNamespace

from services.transcript.whisper_service import transcribe_audio


class _Segment:
    def __init__(self, text: str):
        self.text = text


def _install_fake_modules(monkeypatch):
    class FakeWhisperModel:
        instance = None

        def __init__(self, *args, **kwargs):
            self.init_args = args
            self.init_kwargs = kwargs
            self.calls = []
            FakeWhisperModel.instance = self

        def transcribe(self, audio_path, language=None, beam_size=5):
            self.calls.append(
                {
                    "audio_path": audio_path,
                    "language": language,
                    "beam_size": beam_size,
                }
            )
            if language is None:
                info = SimpleNamespace(language="ko", language_probability=0.98)
                return [_Segment("안녕하세요"), _Segment("테스트입니다")], info

            info = SimpleNamespace(language=language, language_probability=0.99)
            return [_Segment("hello"), _Segment("world")], info

    fake_whisper = ModuleType("faster_whisper")
    fake_whisper.WhisperModel = FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_whisper)

    fake_torch = ModuleType("torch")
    fake_torch.cuda = SimpleNamespace(is_available=lambda: False)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    return FakeWhisperModel


def test_transcribe_audio_uses_auto_detection_when_language_is_none(monkeypatch):
    fake_model_cls = _install_fake_modules(monkeypatch)

    result = transcribe_audio("/tmp/audio.wav", language=None)

    assert result == "안녕하세요 테스트입니다"
    assert fake_model_cls.instance is not None
    assert fake_model_cls.instance.calls == [
        {
            "audio_path": "/tmp/audio.wav",
            "language": None,
            "beam_size": 5,
        }
    ]


def test_transcribe_audio_forces_english_when_language_is_en(monkeypatch):
    fake_model_cls = _install_fake_modules(monkeypatch)

    result = transcribe_audio("/tmp/audio.wav", language="en")

    assert result == "hello world"
    assert fake_model_cls.instance is not None
    assert fake_model_cls.instance.calls == [
        {
            "audio_path": "/tmp/audio.wav",
            "language": "en",
            "beam_size": 5,
        }
    ]
