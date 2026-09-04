from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor in {path}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


card_path = ROOT / "frontend" / "components" / "result" / "ResultCard.tsx"
replace_once(
    card_path,
    "const NOTEBOOKLM_ENABLED = process.env.NEXT_PUBLIC_NOTEBOOKLM_ENABLED === 'true';\n",
    "const NOTEBOOKLM_ENABLED = process.env.NEXT_PUBLIC_NOTEBOOKLM_ENABLED === 'true';\n"
    "const ANKI_EXPORT_STYLES = new Set(['quiz', 'retention_cards']);\n",
    "Anki supported style registry",
)
replace_once(
    card_path,
    "  const linkedNoteId = report.knowledge_note_id;\n",
    "  const linkedNoteId = report.knowledge_note_id;\n"
    "  const canExportAnki = ANKI_EXPORT_STYLES.has(report.style);\n",
    "Anki menu capability",
)
replace_once(
    card_path,
    """              <DropdownMenuItem onClick={() => handleExportFormat('anki')}>
                <Layers className=\"h-3.5 w-3.5 mr-2\" />
                Anki 덱 (.apkg)
              </DropdownMenuItem>
""",
    """              {canExportAnki && (
                <DropdownMenuItem onClick={() => handleExportFormat('anki')}>
                  <Layers className=\"h-3.5 w-3.5 mr-2\" />
                  Anki 덱 (.apkg)
                </DropdownMenuItem>
              )}
""",
    "conditional Anki menu",
)

contract = '''from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_anki_route_and_frontend_contract_are_connected():
    routes = (ROOT / "routes" / "export_routes.py").read_text(encoding="utf-8")
    api = (ROOT / "frontend" / "lib" / "api.ts").read_text(encoding="utf-8")
    card = (ROOT / "frontend" / "components" / "result" / "ResultCard.tsx").read_text(encoding="utf-8")

    assert "@blog_bp.route('/api/export/anki', methods=['POST'])" in routes
    assert "@require_auth\\ndef export_anki" in routes
    assert "X-Anki-Card-Count" in routes
    assert "format: 'markdown' | 'anki'" in api
    assert "const ANKI_EXPORT_STYLES = new Set(['quiz', 'retention_cards'])" in card
    assert "const canExportAnki = ANKI_EXPORT_STYLES.has(report.style)" in card
    assert "{canExportAnki && (" in card
    assert "Anki 덱 (.apkg)" in card
    assert "source_url: report.url" in card
'''
(ROOT / "tests" / "test_anki_export_contract.py").write_text(contract, encoding="utf-8")

print("[OK] staged PR #140 review fixes")
