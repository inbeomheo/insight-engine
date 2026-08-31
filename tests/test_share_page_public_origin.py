from services.content.share_page_service import SharePageStore, render_share_html


def test_get_rewrites_legacy_share_url_to_current_public_origin(tmp_path):
    legacy = SharePageStore(tmp_path, origin="https://heo-mini-surver.tailf0cfa8.ts.net")
    created = legacy.create({"title": "공유 제목", "content": "공유 내용"})

    public = SharePageStore(tmp_path, origin="https://insight.fiv.co.kr")
    loaded = public.get(created["id"])

    assert loaded["share_url"] == f"https://insight.fiv.co.kr/share/{created['id']}"


def test_share_html_has_public_canonical_and_social_metadata():
    item = {
        "id": "Abcdefgh1234",
        "title": "공유 제목",
        "content": "공유 내용",
        "html": "<p>공유 내용</p>",
        "share_url": "https://insight.fiv.co.kr/share/Abcdefgh1234",
        "created_at": "2026-08-31T00:00:00+00:00",
    }

    html = render_share_html(item)

    assert '<link rel="canonical" href="https://insight.fiv.co.kr/share/Abcdefgh1234">' in html
    assert '<meta property="og:url" content="https://insight.fiv.co.kr/share/Abcdefgh1234">' in html
    assert '<meta property="og:site_name" content="Insight Engine">' in html
    assert '<title>공유 제목 · Insight Engine</title>' in html
