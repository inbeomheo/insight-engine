from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_anki_route_and_frontend_contract_are_connected():
    routes = (ROOT / "routes" / "export_routes.py").read_text(encoding="utf-8")
    api = (ROOT / "frontend" / "lib" / "api.ts").read_text(encoding="utf-8")
    card = (ROOT / "frontend" / "components" / "result" / "ResultCard.tsx").read_text(encoding="utf-8")

    assert "@blog_bp.route('/api/export/anki', methods=['POST'])" in routes
    assert "@require_auth\ndef export_anki" in routes
    assert "X-Anki-Card-Count" in routes
    assert "format: 'markdown' | 'anki'" in api
    assert "const ANKI_EXPORT_STYLES = new Set(['quiz', 'retention_cards'])" in card
    assert "const canExportAnki = ANKI_EXPORT_STYLES.has(report.style)" in card
    assert "{canExportAnki && (" in card
    assert "Anki 덱 (.apkg)" in card
    assert "source_url: report.url" in card
