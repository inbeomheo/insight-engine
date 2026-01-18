"""
US-008: 패널 리사이즈 기능
Acceptance Criteria 검증 테스트
"""
import os
import pytest


class TestPanelResizeContract:
    """패널 리사이즈 기능 구현 검증 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 환경 설정"""
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_resize_handle_css_exists(self):
        """리사이즈 핸들 CSS 스타일이 존재하는지 확인"""
        html_path = os.path.join(self.base_dir, 'templates', 'index.html')
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 리사이즈 핸들 CSS 스타일 확인
        assert '.resize-handle' in content, "리사이즈 핸들 CSS 클래스가 없습니다"
        assert '.resize-handle-grip' in content, "리사이즈 그립 CSS 클래스가 없습니다"
        assert 'col-resize' in content, "col-resize 커서 스타일이 없습니다"

    def test_resize_handle_hover_styles(self):
        """리사이즈 핸들 호버 스타일이 존재하는지 확인"""
        html_path = os.path.join(self.base_dir, 'templates', 'index.html')
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.resize-handle:hover' in content, "핸들 호버 스타일이 없습니다"
        assert '.resize-handle.active' in content, "핸들 활성 스타일이 없습니다"

    def test_resize_handle_accessibility(self):
        """리사이즈 핸들 접근성 스타일이 존재하는지 확인"""
        html_path = os.path.join(self.base_dir, 'templates', 'index.html')
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert '.resize-handle:focus' in content, "핸들 포커스 스타일이 없습니다"

    def test_panel_resize_manager_exists(self):
        """PanelResizeManager 모듈이 존재하는지 확인"""
        js_path = os.path.join(self.base_dir, 'static', 'js', 'modules', 'PanelResizeManager.js')
        assert os.path.exists(js_path), "PanelResizeManager.js 파일이 없습니다"

    def test_panel_resize_manager_has_required_methods(self):
        """PanelResizeManager에 필수 메서드가 있는지 확인"""
        js_path = os.path.join(self.base_dir, 'static', 'js', 'modules', 'PanelResizeManager.js')
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 필수 메서드 확인
        assert 'init()' in content, "init 메서드가 없습니다"
        assert 'createResizeHandles()' in content, "createResizeHandles 메서드가 없습니다"
        assert 'startResize(' in content, "startResize 메서드가 없습니다"
        assert 'onResize(' in content, "onResize 메서드가 없습니다"
        assert 'stopResize()' in content, "stopResize 메서드가 없습니다"

    def test_panel_resize_manager_has_limits(self):
        """PanelResizeManager에 최소/최대 너비 제한이 있는지 확인"""
        js_path = os.path.join(self.base_dir, 'static', 'js', 'modules', 'PanelResizeManager.js')
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 제한 설정 확인
        assert 'limits' in content, "limits 설정이 없습니다"
        assert 'min:' in content, "min 설정이 없습니다"
        assert 'max:' in content, "max 설정이 없습니다"
        assert '280' in content, "최소 너비 설정이 없습니다"
        assert '500' in content, "최대 너비 설정이 없습니다"

    def test_panel_resize_manager_has_storage(self):
        """PanelResizeManager에 localStorage 저장 기능이 있는지 확인"""
        js_path = os.path.join(self.base_dir, 'static', 'js', 'modules', 'PanelResizeManager.js')
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # localStorage 관련 메서드 확인
        assert 'storageKey' in content, "storageKey가 없습니다"
        assert 'loadSavedSizes()' in content, "loadSavedSizes 메서드가 없습니다"
        assert 'saveSizes()' in content, "saveSizes 메서드가 없습니다"
        assert 'localStorage' in content, "localStorage 사용이 없습니다"

    def test_panel_resize_manager_keyboard_support(self):
        """PanelResizeManager에 키보드 접근성이 있는지 확인"""
        js_path = os.path.join(self.base_dir, 'static', 'js', 'modules', 'PanelResizeManager.js')
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 키보드 접근성 확인
        assert 'handleKeyboard' in content, "handleKeyboard 메서드가 없습니다"
        assert 'ArrowLeft' in content, "ArrowLeft 키 지원이 없습니다"
        assert 'ArrowRight' in content, "ArrowRight 키 지원이 없습니다"

    def test_main_js_imports_panel_resize_manager(self):
        """main.js에서 PanelResizeManager를 import하는지 확인"""
        js_path = os.path.join(self.base_dir, 'static', 'js', 'main.js')
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'PanelResizeManager' in content, "main.js에서 PanelResizeManager를 import하지 않습니다"
        assert "from './modules/PanelResizeManager.js'" in content, "PanelResizeManager import 경로가 잘못되었습니다"

    def test_main_js_initializes_panel_resize_manager(self):
        """main.js에서 PanelResizeManager를 초기화하는지 확인"""
        js_path = os.path.join(self.base_dir, 'static', 'js', 'main.js')
        with open(js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'new PanelResizeManager()' in content, "PanelResizeManager 인스턴스 생성이 없습니다"
        assert 'panelResizeManager.init()' in content, "panelResizeManager.init() 호출이 없습니다"

    def test_responsive_resize_handle_hidden_on_small_screens(self):
        """작은 화면에서 리사이즈 핸들이 숨겨지는지 확인"""
        html_path = os.path.join(self.base_dir, 'templates', 'index.html')
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 미디어 쿼리로 핸들 숨김 확인
        assert '@media (max-width: 1279px)' in content, "작은 화면 미디어 쿼리가 없습니다"
        assert 'display: none !important' in content, "핸들 숨김 스타일이 없습니다"
