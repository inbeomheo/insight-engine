"""
Chrome 확장 프로그램 구조 및 파일 유효성 테스트
빌드 도구 없이 순수 파일 구조 검증
"""
import json
import os
import pytest

EXTENSION_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "extensions",
    "chrome",
)


# ── 필수 파일 존재 확인 ────────────────────────────────────────────────────────

REQUIRED_FILES = [
    "manifest.json",
    "background.js",
    "content.js",
    "content.css",
    "popup.html",
    "popup.js",
    "sidepanel.html",
    "sidepanel.js",
    "icons/icon16.png",
    "icons/icon48.png",
    "icons/icon128.png",
]


@pytest.mark.parametrize("filename", REQUIRED_FILES)
def test_required_file_exists(filename):
    """필수 파일이 모두 존재하는지 확인합니다"""
    path = os.path.join(EXTENSION_DIR, filename)
    assert os.path.exists(path), f"필수 파일 없음: {filename}"
    assert os.path.getsize(path) > 0, f"파일이 비어 있음: {filename}"


# ── manifest.json 구조 검증 ───────────────────────────────────────────────────

@pytest.fixture
def manifest():
    path = os.path.join(EXTENSION_DIR, "manifest.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_manifest_version(manifest):
    """Manifest V3 여부 확인"""
    assert manifest.get("manifest_version") == 3, "manifest_version은 3이어야 합니다"


def test_manifest_name(manifest):
    """확장 프로그램 이름 확인"""
    assert manifest.get("name"), "name 필드가 없습니다"
    assert len(manifest["name"]) > 0


def test_manifest_version_field(manifest):
    """버전 필드 형식 확인 (x.y.z)"""
    version = manifest.get("version", "")
    parts = version.split(".")
    assert len(parts) >= 2, f"버전 형식 오류: {version}"
    assert all(part.isdigit() for part in parts), f"버전에 숫자 외 문자: {version}"


def test_manifest_permissions(manifest):
    """필수 권한 포함 확인"""
    permissions = manifest.get("permissions", [])
    required = {"activeTab", "storage", "sidePanel"}
    missing = required - set(permissions)
    assert not missing, f"필수 권한 누락: {missing}"


def test_manifest_host_permissions(manifest):
    """YouTube 호스트 권한 포함 확인"""
    host_perms = manifest.get("host_permissions", [])
    assert any("youtube.com" in p for p in host_perms), \
        "youtube.com 호스트 권한이 없습니다"


def test_manifest_background(manifest):
    """백그라운드 서비스 워커 설정 확인"""
    bg = manifest.get("background", {})
    assert bg.get("service_worker") == "background.js", \
        "background.service_worker가 background.js가 아닙니다"


def test_manifest_content_scripts(manifest):
    """콘텐츠 스크립트 설정 확인"""
    scripts = manifest.get("content_scripts", [])
    assert len(scripts) > 0, "content_scripts가 없습니다"

    script = scripts[0]
    assert "https://www.youtube.com/watch*" in script.get("matches", []), \
        "YouTube watch URL 매칭이 없습니다"
    assert "content.js" in script.get("js", []), "content.js가 없습니다"
    assert "content.css" in script.get("css", []), "content.css가 없습니다"


def test_manifest_action(manifest):
    """팝업 액션 설정 확인"""
    action = manifest.get("action", {})
    assert action.get("default_popup") == "popup.html", \
        "default_popup이 popup.html이 아닙니다"


def test_manifest_side_panel(manifest):
    """사이드패널 설정 확인"""
    side_panel = manifest.get("side_panel", {})
    assert side_panel.get("default_path") == "sidepanel.html", \
        "side_panel.default_path가 sidepanel.html이 아닙니다"


def test_manifest_icons(manifest):
    """아이콘 설정 확인"""
    icons = manifest.get("icons", {})
    required_sizes = {"16", "48", "128"}
    missing = required_sizes - set(icons.keys())
    assert not missing, f"아이콘 크기 누락: {missing}"


def test_manifest_referenced_files_exist(manifest):
    """manifest.json에서 참조하는 파일들이 실제로 존재하는지 확인"""
    refs = []

    # background
    bg = manifest.get("background", {})
    if sw := bg.get("service_worker"):
        refs.append(sw)

    # action
    action = manifest.get("action", {})
    if popup := action.get("default_popup"):
        refs.append(popup)

    # side panel
    sp = manifest.get("side_panel", {})
    if path := sp.get("default_path"):
        refs.append(path)

    # content scripts
    for script in manifest.get("content_scripts", []):
        refs.extend(script.get("js", []))
        refs.extend(script.get("css", []))

    for ref in refs:
        path = os.path.join(EXTENSION_DIR, ref)
        assert os.path.exists(path), f"manifest 참조 파일이 없음: {ref}"


# ── JS 파일 기본 구조 확인 ────────────────────────────────────────────────────

def _read(filename):
    path = os.path.join(EXTENSION_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_background_js_has_message_listener():
    """background.js에 메시지 핸들러가 있는지 확인"""
    content = _read("background.js")
    assert "onMessage.addListener" in content, \
        "background.js에 chrome.runtime.onMessage.addListener가 없습니다"


def test_background_js_has_generate_function():
    """background.js에 generateContent 함수가 있는지 확인"""
    content = _read("background.js")
    assert "generateContent" in content, \
        "background.js에 generateContent 함수가 없습니다"


def test_content_js_has_button_injection():
    """content.js에 버튼 삽입 로직이 있는지 확인"""
    content = _read("content.js")
    assert "insight-engine-btn" in content, \
        "content.js에 버튼 ID가 없습니다"


def test_content_js_has_sidepanel_open():
    """content.js에 사이드패널 열기 로직이 있는지 확인"""
    content = _read("content.js")
    assert "openSidePanel" in content, \
        "content.js에 openSidePanel 함수가 없습니다"


def test_sidepanel_js_has_generate():
    """sidepanel.js에 generate 함수가 있는지 확인"""
    content = _read("sidepanel.js")
    assert "generate" in content, \
        "sidepanel.js에 generate 함수가 없습니다"


def test_popup_js_has_connection_test():
    """popup.js에 연결 테스트 로직이 있는지 확인"""
    content = _read("popup.js")
    assert "checkConnection" in content, \
        "popup.js에 checkConnection이 없습니다"


# ── HTML 파일 구조 확인 ───────────────────────────────────────────────────────

def test_popup_html_has_server_url_input():
    """popup.html에 서버 URL 입력란이 있는지 확인"""
    content = _read("popup.html")
    assert "server-url" in content, "popup.html에 server-url 입력란이 없습니다"


def test_popup_html_includes_popup_js():
    """popup.html이 popup.js를 로드하는지 확인"""
    content = _read("popup.html")
    assert "popup.js" in content, "popup.html에 popup.js 스크립트 태그가 없습니다"


def test_sidepanel_html_has_generate_btn():
    """sidepanel.html에 생성 버튼이 있는지 확인"""
    content = _read("sidepanel.html")
    assert "generate-btn" in content, "sidepanel.html에 generate-btn이 없습니다"


def test_sidepanel_html_includes_sidepanel_js():
    """sidepanel.html이 sidepanel.js를 로드하는지 확인"""
    content = _read("sidepanel.html")
    assert "sidepanel.js" in content, "sidepanel.html에 sidepanel.js 스크립트 태그가 없습니다"


def test_sidepanel_html_has_style_selector():
    """sidepanel.html에 스타일 선택 UI가 있는지 확인"""
    content = _read("sidepanel.html")
    assert "style-chip" in content, "sidepanel.html에 스타일 선택 UI가 없습니다"


# ── PNG 파일 형식 확인 ────────────────────────────────────────────────────────

@pytest.mark.parametrize("size", [16, 48, 128])
def test_icon_is_valid_png(size):
    """아이콘 파일이 유효한 PNG인지 확인 (PNG 시그니처 검사)"""
    path = os.path.join(EXTENSION_DIR, "icons", f"icon{size}.png")
    with open(path, "rb") as f:
        header = f.read(8)
    # PNG 시그니처: 89 50 4E 47 0D 0A 1A 0A
    assert header == b'\x89PNG\r\n\x1a\n', \
        f"icon{size}.png가 유효한 PNG 파일이 아닙니다"
