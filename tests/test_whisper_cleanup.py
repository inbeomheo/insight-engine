from services.transcript.whisper_service import _cleanup_file


def test_cleanup_file_deletes_existing_file(tmp_path):
    target = tmp_path / "audio.wav"
    target.write_text("temporary audio", encoding="utf-8")

    assert target.exists()

    _cleanup_file(str(target))

    assert not target.exists()


def test_cleanup_file_ignores_missing_file(tmp_path):
    missing = tmp_path / "missing.wav"

    _cleanup_file(str(missing))

    assert not missing.exists()


def test_cleanup_file_ignores_none_input():
    _cleanup_file(None)  # type: ignore[arg-type]
