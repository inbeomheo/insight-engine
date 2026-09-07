"""CSP regression coverage for the public server-rendered share page."""
from __future__ import annotations

import re

from app import create_app


def test_share_page_inline_style_uses_per_response_nonce(tmp_path):
    app = create_app({
        'TESTING': True,
        'SHARE_PAGE_DIR': str(tmp_path / 'shares'),
    })
    client = app.test_client()

    created = client.post(
        '/api/shares',
        json={'title': 'Safe share', 'content': '# Heading\n\nBody'},
    )
    assert created.status_code == 201

    response = client.get(f"/share/{created.get_json()['id']}")
    assert response.status_code == 200
    policy = response.headers['Content-Security-Policy']
    assert "'unsafe-inline'" not in policy
    nonce_match = re.search(r"style-src 'nonce-([^']+)'", policy)
    assert nonce_match is not None
    assert f'<style nonce="{nonce_match.group(1)}">' in response.get_data(as_text=True)


def test_share_page_preserves_safe_mathml_and_removes_active_content(tmp_path):
    app = create_app({
        'TESTING': True,
        'SHARE_PAGE_DIR': str(tmp_path / 'shares'),
    })
    client = app.test_client()
    mathml = (
        '<span class="katex-display"><math display="block" onclick="alert(1)">'
        '<semantics><mrow><msup><mi>x</mi><mn>2</mn></msup></mrow>'
        '<annotation encoding="application/x-tex">x^2</annotation></semantics>'
        '</math></span><script>alert(1)</script>'
    )

    created = client.post(
        '/api/shares',
        json={'title': 'Math share', 'content': '$$x^2$$', 'html': mathml},
    )
    assert created.status_code == 201

    response = client.get(f"/share/{created.get_json()['id']}")
    body = response.get_data(as_text=True)
    assert '<math display="block">' in body
    assert '<msup>' in body
    assert 'encoding="application/x-tex"' in body
    assert '.katex-display' in body
    assert 'onclick=' not in body
    assert '<script' not in body
