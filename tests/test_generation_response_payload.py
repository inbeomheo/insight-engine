from routes.generation_helpers import _build_generation_response_payload


def test_build_generation_response_payload_preserves_contract_fields():
    payload = _build_generation_response_payload(
        result={"title": "T", "content": "Body", "html": "<p>Body</p>"},
        report_id="rid-1",
        used_prompt="prompt text",
        elapsed_time=1.23,
        youtube_title="Source title",
        raw_transcript="Transcript",
        transcript_source="api",
        style="unknown_style",
        comments=["c1"],
        comment_result={"content": "summary"},
        seo={"description": "d"},
        geo={"entities": []},
        faq_schema={"mainEntity": []},
        cta={"text": "go"},
        json_ld_schemas=[{"@type": "VideoObject"}],
        quality_score={"grade": "A"},
        web_sources=[{"url": "https://example.com"}],
        analysis={"score": 0.9},
        transcript_segments=[{"start": 0, "text": "hi"}],
        chapters=[{"title": "Intro"}],
        total_duration_seconds=42,
        quota={"remaining": 9},
        agent_meta={"agent_mode": True},
    )

    assert payload["id"] == "rid-1"
    assert payload["prompt_length"] == len("prompt text")
    assert payload["youtube_title"] == "Source title"
    assert payload["style_label"] == "unknown_style"
    assert payload["comment_summary_included"] is True
    assert payload["web_sources"] == [{"url": "https://example.com"}]
    assert payload["transcript_segments"] == [{"start": 0, "text": "hi"}]
    assert payload["chapters"] == [{"title": "Intro"}]
    assert payload["total_duration_seconds"] == 42
    assert payload["quota"] == {"remaining": 9}
    assert payload["agent_mode"] is True


def test_build_generation_response_payload_defaults_optional_collections():
    payload = _build_generation_response_payload(
        result={"title": "T", "content": "Body"},
        report_id="rid-2",
        used_prompt=None,
        elapsed_time=0,
        youtube_title="Source",
        raw_transcript="Raw",
        transcript_source="cache",
        style="unknown_style",
        comments=[],
        comment_result=None,
        quota={},
    )

    assert payload["prompt_length"] == 0
    assert payload["comment_summary_included"] is False
    assert payload["transcript_segments"] == []
    assert payload["chapters"] == []
