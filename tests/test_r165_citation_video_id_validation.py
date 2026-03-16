"""R165: citation_service video_id 검증 테스트"""
import pytest
from services.content.citation_service import (
    enrich_content_with_links,
    enrich_html_with_links,
    _validate_video_id,
)


class TestValidateVideoId:

    def test_valid_11char_id(self):
        assert _validate_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_valid_with_hyphen_underscore(self):
        assert _validate_video_id("abc-_12DEfg") == "abc-_12DEfg"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            _validate_video_id("")

    def test_none_raises(self):
        with pytest.raises(ValueError):
            _validate_video_id(None)

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            _validate_video_id("abc123")

    def test_too_long_raises(self):
        with pytest.raises(ValueError):
            _validate_video_id("dQw4w9WgXcQx")

    def test_special_chars_raises(self):
        with pytest.raises(ValueError):
            _validate_video_id('"><script>x')

    def test_path_traversal_raises(self):
        with pytest.raises(ValueError):
            _validate_video_id("../etc/pass")


class TestEnrichContentValidation:

    def test_valid_id_enriches(self):
        result = enrich_content_with_links("text [01:30] more", "dQw4w9WgXcQ")
        assert "youtube.com/watch?v=dQw4w9WgXcQ&t=90s" in result

    def test_invalid_id_raises(self):
        with pytest.raises(ValueError):
            enrich_content_with_links("text [01:30]", "short")

    def test_empty_id_raises(self):
        with pytest.raises(ValueError):
            enrich_content_with_links("text [01:30]", "")


class TestEnrichHtmlValidation:

    def test_valid_id_enriches(self):
        result = enrich_html_with_links("<p>[02:00] text</p>", "dQw4w9WgXcQ")
        assert "youtube.com/watch?v=dQw4w9WgXcQ&t=120s" in result

    def test_invalid_id_raises(self):
        with pytest.raises(ValueError):
            enrich_html_with_links("<p>[01:30]</p>", "too_long_id_xx")

    def test_none_id_raises(self):
        with pytest.raises(ValueError):
            enrich_html_with_links("<p>[01:30]</p>", None)
