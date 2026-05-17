"""RSS feed service tests."""

from xml.etree import ElementTree

from services.content.rss_feed_service import build_rss_feed_xml


def parse_feed(xml: str):
    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>\n')
    return ElementTree.fromstring(xml.split("\n", 1)[1])


def test_build_rss_feed_xml_returns_channel_metadata():
    root = parse_feed(build_rss_feed_xml("https://example.com", []))
    channel = root.find("channel")

    assert root.tag == "rss"
    assert root.attrib == {"version": "2.0"}
    assert channel.findtext("title") == "Insight Engine"
    assert channel.findtext("link") == "https://example.com"
    assert channel.findtext("description") == "AI? ??? ?? ??? ??"
    assert channel.findtext("language") == "ko"
    assert channel.findall("item") == []


def test_build_rss_feed_xml_adds_history_items_and_guid_when_present():
    root = parse_feed(
        build_rss_feed_xml(
            "https://example.com",
            [
                {
                    "title": "? ?",
                    "content": "??",
                    "created_at": "2026-05-17T10:00:00Z",
                    "report_id": "r-1",
                }
            ],
        )
    )
    item = root.find("channel").find("item")

    assert item.findtext("title") == "? ?"
    assert item.findtext("description") == "??"
    assert item.findtext("pubDate") == "2026-05-17T10:00:00Z"
    assert item.findtext("guid") == "r-1"


def test_build_rss_feed_xml_matches_existing_defaults_and_truncates_description():
    root = parse_feed(
        build_rss_feed_xml(
            "https://example.com",
            [
                {
                    "content": "?" * 501,
                    "created_at": None,
                    "report_id": "",
                }
            ],
        )
    )
    item = root.find("channel").find("item")

    assert item.findtext("title") == "?? ??"
    assert item.findtext("description") == "?" * 500
    assert item.findtext("pubDate") == ""
    assert item.find("guid") is None
