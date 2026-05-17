"""RSS feed XML helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring


def build_rss_feed_xml(
    channel_link: str,
    items: Iterable[Mapping[str, Any]],
) -> str:
    """Build the RSS 2.0 feed XML string for generated content history."""
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "Insight Engine"
    SubElement(channel, "link").text = channel_link
    SubElement(channel, "description").text = "AI? ??? ?? ??? ??"
    SubElement(channel, "language").text = "ko"

    for item_data in items:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = item_data.get("title", "?? ??")
        SubElement(item, "description").text = (item_data.get("content", "") or "")[:500]
        SubElement(item, "pubDate").text = item_data.get("created_at", "")
        report_id = item_data.get("report_id", "")
        if report_id:
            SubElement(item, "guid").text = report_id

    xml_body = tostring(rss, encoding="unicode", xml_declaration=False)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_body
