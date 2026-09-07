from agent.toolsets import resolve_toolset_names


def test_full_toolset_does_not_auto_expose_publish_or_schedule_toolsets():
    names = resolve_toolset_names(["full"])

    assert "mcp" not in names
    assert "schedule" not in names
    assert "mcp" in resolve_toolset_names(["role_publisher"])
    assert "schedule" in resolve_toolset_names(["role_publisher"])


def test_media_auto_wrapper_skips_cleanup_and_unbounded_video_extractors():
    from agent.registry import registry
    from agent.tools import media_tools

    assert {"video_clip_service", "video_deepdive_service"} <= media_tools._SKIP_MODULES
    assert registry.get("cleanup_clips") is None
    assert registry.get("build_visual_deepdive_from_video") is None
