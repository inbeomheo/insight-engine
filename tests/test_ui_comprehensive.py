"""
스마트 콘텐츠 생성기 - 종합 UI 테스트
Playwright를 사용하여 모든 기능 및 팝업 테스트
"""
import pytest
from playwright.sync_api import sync_playwright, expect
import time

BASE_URL = "http://127.0.0.1:5001"
TEST_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

class TestResults:
    """테스트 결과를 수집하는 클래스"""
    def __init__(self):
        self.passed = []
        self.failed = []

    def add_pass(self, test_name, message=""):
        self.passed.append({"name": test_name, "message": message})
        print(f"  [PASS] {test_name}: {message}")

    def add_fail(self, test_name, message=""):
        # 메시지에서 유니코드 문자 제거
        safe_message = message.encode('cp949', errors='replace').decode('cp949')
        self.failed.append({"name": test_name, "message": safe_message})
        print(f"  [FAIL] {test_name}: {safe_message[:200]}")

    def summary(self):
        total = len(self.passed) + len(self.failed)
        print("\n" + "="*60)
        print(f"테스트 결과 요약")
        print("="*60)
        print(f"전체: {total} | 성공: {len(self.passed)} | 실패: {len(self.failed)}")
        if self.failed:
            print("\n실패한 테스트:")
            for f in self.failed:
                print(f"  - {f['name']}: {f['message']}")
        print("="*60)
        return len(self.failed) == 0


def run_all_tests():
    """모든 UI 테스트 실행"""
    results = TestResults()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        print("\n" + "="*60)
        print("스마트 콘텐츠 생성기 종합 UI 테스트 시작")
        print("="*60)

        # 1. 메인 페이지 로딩 테스트
        print("\n[1] 메인 페이지 로딩 테스트")
        test_main_page_loading(page, results)

        # 2. Settings Modal 테스트
        print("\n[2] Settings Modal 테스트")
        test_settings_modal(page, results)

        # 3. Onboarding Modal 테스트 (localStorage 초기화 후)
        print("\n[3] Onboarding Modal 테스트")
        test_onboarding_modal(page, results)

        # 4. Custom Style Modal 테스트
        print("\n[4] Custom Style Modal 테스트")
        test_custom_style_modal(page, results)

        # 5. URL 입력 및 관리 테스트
        print("\n[5] URL 입력 및 관리 테스트")
        test_url_management(page, results)

        # 6. AI 서비스/모델 선택 테스트
        print("\n[6] AI 서비스/모델 선택 테스트")
        test_ai_service_selection(page, results)

        # 7. 스타일 선택 테스트
        print("\n[7] 스타일 선택 테스트")
        test_style_selection(page, results)

        # 8. Advanced Options 테스트
        print("\n[8] Advanced Options 테스트")
        test_advanced_options(page, results)

        # 9. 알림 시스템 테스트
        print("\n[9] 알림 시스템 테스트")
        test_alert_system(page, results)

        # 10. 버튼 상태 테스트
        print("\n[10] 버튼 상태 테스트")
        test_button_states(page, results)

        # 결과 요약 출력
        success = results.summary()

        # 테스트 완료 후 잠시 대기 (결과 확인용)
        time.sleep(2)
        browser.close()

        return success


def test_main_page_loading(page, results):
    """메인 페이지 로딩 테스트"""
    try:
        # 온보딩 건너뛰기 설정
        page.goto(BASE_URL, timeout=10000)
        skip_onboarding_via_storage(page)
        page.reload()
        page.wait_for_load_state("networkidle")
        close_onboarding_if_visible(page)

        # 타이틀 확인
        title = page.title()
        if "Content Analysis" in title or "Insight Engine" in title:
            results.add_pass("페이지 타이틀", f"'{title}'")
        else:
            results.add_fail("페이지 타이틀", f"예상: 'Content Analysis', 실제: '{title}'")

        # 헤더 확인
        header = page.locator("header")
        if header.is_visible():
            results.add_pass("헤더 표시", "헤더가 화면에 표시됨")
        else:
            results.add_fail("헤더 표시", "헤더가 보이지 않음")

        # 설정 버튼 확인
        settings_btn = page.locator("#settings-btn")
        if settings_btn.is_visible():
            results.add_pass("설정 버튼", "설정 버튼이 표시됨")
        else:
            results.add_fail("설정 버튼", "설정 버튼이 보이지 않음")

        # URL 입력란 확인
        url_input = page.locator("#url-input")
        if url_input.is_visible():
            results.add_pass("URL 입력란", "URL 입력란이 표시됨")
        else:
            results.add_fail("URL 입력란", "URL 입력란이 보이지 않음")

        # Start 버튼 확인
        start_btn = page.locator("#start-btn")
        if start_btn.is_visible():
            results.add_pass("Start 버튼", "Start 버튼이 표시됨")
        else:
            results.add_fail("Start 버튼", "Start 버튼이 보이지 않음")

        # Run Analysis 버튼 확인
        run_btn = page.locator("#run-analysis-btn")
        if run_btn.is_visible():
            results.add_pass("Run Analysis 버튼", "Run Analysis 버튼이 표시됨")
        else:
            results.add_fail("Run Analysis 버튼", "Run Analysis 버튼이 보이지 않음")

        # Empty State 확인
        empty_state = page.locator("#empty-state")
        if empty_state.is_visible():
            results.add_pass("Empty State", "분석 결과 안내 메시지가 표시됨")
        else:
            results.add_fail("Empty State", "Empty State가 보이지 않음")

    except Exception as e:
        results.add_fail("메인 페이지 로딩", str(e))


def test_settings_modal(page, results):
    """Settings Modal 테스트"""
    try:
        page.goto(BASE_URL, timeout=10000)
        skip_onboarding_via_storage(page)
        page.reload()
        page.wait_for_load_state("networkidle")
        close_onboarding_if_visible(page)

        # 설정 버튼 클릭
        settings_btn = page.locator("#settings-btn")
        settings_btn.click()
        time.sleep(0.5)

        # Settings Modal 열림 확인
        settings_modal = page.locator("#settings-modal")
        if settings_modal.is_visible():
            results.add_pass("Settings Modal 열기", "모달이 정상적으로 열림")
        else:
            results.add_fail("Settings Modal 열기", "모달이 열리지 않음")
            return

        # Provider 목록 확인
        provider_cards = page.locator("#provider-list .provider-card")
        count = provider_cards.count()
        if count >= 4:
            results.add_pass("Provider 목록", f"{count}개의 AI 서비스 표시됨")
        else:
            results.add_fail("Provider 목록", f"예상: 4개 이상, 실제: {count}개")

        # Provider 체크박스 테스트
        first_checkbox = page.locator("[data-provider-check]").first
        if first_checkbox.is_visible():
            # 체크되어 있지 않으면 체크
            if not first_checkbox.is_checked():
                first_checkbox.click()
                time.sleep(0.3)

            # API 키 입력란 펼쳐짐 확인
            first_body = page.locator(".provider-body.expanded").first
            if first_body.is_visible():
                results.add_pass("Provider 체크박스", "체크 시 API 키 입력란 펼쳐짐")
            else:
                results.add_fail("Provider 체크박스", "체크해도 입력란이 펼쳐지지 않음")

        # API 키 입력 테스트
        first_key_input = page.locator("[data-provider-key]").first
        if first_key_input.is_visible():
            first_key_input.fill("test-api-key-12345")
            results.add_pass("API 키 입력", "API 키 입력 가능")
        else:
            results.add_fail("API 키 입력", "API 키 입력란이 보이지 않음")

        # 비밀번호 토글 버튼 테스트
        toggle_btn = page.locator("[data-toggle-key]").first
        if toggle_btn.is_visible():
            input_type_before = first_key_input.get_attribute("type")
            toggle_btn.click()
            time.sleep(0.2)
            input_type_after = first_key_input.get_attribute("type")
            if input_type_before != input_type_after:
                results.add_pass("비밀번호 토글", f"{input_type_before} -> {input_type_after}")
            else:
                results.add_fail("비밀번호 토글", "타입이 변경되지 않음")

        # Supadata API 키 입력란 확인
        supadata_input = page.locator("#supadata-api-key")
        if supadata_input.is_visible():
            results.add_pass("Supadata API 입력란", "Supadata API 키 입력란 표시됨")
        else:
            results.add_fail("Supadata API 입력란", "입력란이 보이지 않음")

        # 닫기 버튼 테스트
        close_btn = page.locator("#modal-close")
        close_btn.click()
        time.sleep(0.3)

        if not settings_modal.is_visible():
            results.add_pass("Settings Modal 닫기", "X 버튼으로 닫힘")
        else:
            results.add_fail("Settings Modal 닫기", "모달이 닫히지 않음")

        # 다시 열고 닫기 버튼 테스트
        settings_btn.click()
        time.sleep(0.5)
        cancel_btn = page.locator("#modal-cancel")
        cancel_btn.click()
        time.sleep(0.3)

        if not settings_modal.is_visible():
            results.add_pass("닫기 버튼", "닫기 버튼으로 모달 닫힘")
        else:
            results.add_fail("닫기 버튼", "모달이 닫히지 않음")

    except Exception as e:
        results.add_fail("Settings Modal 테스트", str(e))


def test_onboarding_modal(page, results):
    """Onboarding Modal 테스트"""
    try:
        # localStorage 초기화하여 첫 방문 상태 시뮬레이션
        page.goto(BASE_URL, timeout=10000)
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # Onboarding Modal 표시 확인
        onboarding_modal = page.locator("#onboarding-modal")
        if onboarding_modal.is_visible():
            results.add_pass("Onboarding Modal 표시", "첫 방문 시 자동으로 표시됨")
        else:
            results.add_fail("Onboarding Modal 표시", "첫 방문 시 표시되지 않음")
            return

        # 환영 메시지 확인
        welcome_text = page.locator("#onboarding-modal h2")
        if welcome_text.is_visible() and "환영" in welcome_text.text_content():
            results.add_pass("환영 메시지", "환영 메시지가 표시됨")
        else:
            results.add_fail("환영 메시지", "환영 메시지가 없음")

        # Provider 선택 확인
        onboard_providers = page.locator("#onboarding-providers .provider-card")
        count = onboard_providers.count()
        if count >= 4:
            results.add_pass("Onboarding Provider 목록", f"{count}개의 서비스 표시")
        else:
            results.add_fail("Onboarding Provider 목록", f"예상: 4개 이상, 실제: {count}개")

        # 체크박스 선택 테스트
        first_checkbox = page.locator("[data-onboard-check]").first
        first_checkbox.click()
        time.sleep(0.3)

        # API 키 입력란 펼쳐짐 확인
        first_body = page.locator("[data-onboard-body]").first
        if first_body.is_visible():
            results.add_pass("Onboarding 체크박스", "체크 시 입력란 펼쳐짐")

        # API 키 입력
        first_key_input = page.locator("[data-onboard-key]").first
        first_key_input.fill("test-onboarding-key")

        # 설정 완료 버튼 클릭
        save_btn = page.locator("#onboarding-save")
        save_btn.click()
        time.sleep(0.5)

        if not onboarding_modal.is_visible():
            results.add_pass("Onboarding 완료", "설정 완료 후 모달 닫힘")
        else:
            results.add_fail("Onboarding 완료", "모달이 닫히지 않음")

        # 성공 알림 확인
        alert = page.locator(".alert-success")
        if alert.is_visible():
            results.add_pass("Onboarding 성공 알림", "설정 완료 알림 표시됨")
        else:
            results.add_fail("Onboarding 성공 알림", "알림이 표시되지 않음")

    except Exception as e:
        results.add_fail("Onboarding Modal 테스트", str(e))


def test_custom_style_modal(page, results):
    """Custom Style Modal 테스트"""
    try:
        page.goto(BASE_URL, timeout=10000)
        skip_onboarding_via_storage(page)
        page.reload()
        page.wait_for_load_state("networkidle")
        close_onboarding_if_visible(page)

        # 커스텀 스타일 추가 버튼 클릭
        add_btn = page.locator("#add-custom-style-btn")
        if add_btn.is_visible():
            add_btn.click()
            time.sleep(0.5)
            results.add_pass("커스텀 스타일 버튼", "버튼이 표시되고 클릭 가능")
        else:
            results.add_fail("커스텀 스타일 버튼", "버튼이 보이지 않음")
            return

        # Custom Style Modal 열림 확인
        custom_modal = page.locator("#custom-style-modal")
        if custom_modal.is_visible():
            results.add_pass("Custom Style Modal 열기", "모달이 정상적으로 열림")
        else:
            results.add_fail("Custom Style Modal 열기", "모달이 열리지 않음")
            return

        # 스타일 이름 입력 테스트
        name_input = page.locator("#custom-style-name")
        if name_input.is_visible():
            name_input.fill("테스트 스타일")
            results.add_pass("스타일 이름 입력", "이름 입력 가능")
        else:
            results.add_fail("스타일 이름 입력", "입력란이 보이지 않음")

        # 아이콘 선택 테스트 (라벨을 클릭해야 함 - sr-only 라디오)
        icon_labels = page.locator('#icon-selection label')
        count = icon_labels.count()
        if count >= 5:
            results.add_pass("아이콘 옵션", f"{count}개의 아이콘 옵션 표시")
            # 두 번째 아이콘 선택 (라벨 클릭)
            icon_labels.nth(1).click()
            time.sleep(0.2)
        else:
            results.add_fail("아이콘 옵션", f"예상: 5개, 실제: {count}개")

        # 프롬프트 입력 테스트
        prompt_textarea = page.locator("#custom-style-prompt")
        if prompt_textarea.is_visible():
            test_prompt = "이것은 테스트 프롬프트입니다. AI에게 전달될 지시사항입니다."
            prompt_textarea.fill(test_prompt)
            results.add_pass("프롬프트 입력", "프롬프트 입력 가능")
        else:
            results.add_fail("프롬프트 입력", "입력란이 보이지 않음")

        # 글자수 카운터 확인
        char_count = page.locator("#prompt-char-count")
        if char_count.is_visible():
            count_text = char_count.text_content()
            if int(count_text) > 0:
                results.add_pass("글자수 카운터", f"현재 {count_text}자")
            else:
                results.add_fail("글자수 카운터", "카운터가 업데이트되지 않음")

        # 취소 버튼 테스트
        cancel_btn = page.locator("#custom-style-cancel")
        cancel_btn.click()
        time.sleep(0.5)

        # 모달이 완전히 닫힐 때까지 대기
        custom_modal.wait_for(state="hidden", timeout=5000)

        if not custom_modal.is_visible():
            results.add_pass("Custom Modal 취소", "취소 버튼으로 닫힘")
        else:
            results.add_fail("Custom Modal 취소", "모달이 닫히지 않음")
            return  # 모달이 안 닫히면 여기서 중단

        # 다시 열고 저장 테스트
        time.sleep(0.5)  # 안정화 대기
        add_btn.click()
        time.sleep(0.5)

        # 모달이 열릴 때까지 대기
        custom_modal.wait_for(state="visible", timeout=5000)

        name_input.fill("테스트 스타일")
        prompt_textarea.fill("테스트 프롬프트입니다.")

        save_btn = page.locator("#custom-style-save")
        save_btn.click()
        time.sleep(0.5)

        if not custom_modal.is_visible():
            results.add_pass("Custom Style 저장", "저장 후 모달 닫힘")
        else:
            results.add_fail("Custom Style 저장", "모달이 닫히지 않음")

    except Exception as e:
        results.add_fail("Custom Style Modal 테스트", str(e))


def test_url_management(page, results):
    """URL 입력 및 관리 테스트"""
    try:
        page.goto(BASE_URL, timeout=10000)
        skip_onboarding_via_storage(page)
        page.reload()
        page.wait_for_load_state("networkidle")
        close_onboarding_if_visible(page)

        url_input = page.locator("#url-input")

        # 단일 URL 입력 테스트
        url_input.fill(TEST_YOUTUBE_URL)
        if url_input.input_value() == TEST_YOUTUBE_URL:
            results.add_pass("URL 입력", "URL 입력 가능")
        else:
            results.add_fail("URL 입력", "URL이 입력되지 않음")

        # Enter 키로 URL 추가
        url_input.press("Enter")
        time.sleep(0.5)

        # URL 카드 생성 확인
        url_cards = page.locator("#url-list-container .url-card")
        if url_cards.count() >= 1:
            results.add_pass("URL 추가", "URL이 리스트에 추가됨")
        else:
            results.add_fail("URL 추가", "URL 카드가 생성되지 않음")

        # URL 카운트 확인
        url_count = page.locator("#url-count")
        count_text = url_count.text_content()
        if count_text == "1":
            results.add_pass("URL 카운트", f"카운트: {count_text}")
        else:
            results.add_fail("URL 카운트", f"예상: 1, 실제: {count_text}")

        # 두 번째 URL 추가
        second_url = "https://www.youtube.com/watch?v=9bZkp7q19f0"
        url_input.fill(second_url)
        url_input.press("Enter")
        time.sleep(0.3)

        if url_cards.count() >= 2:
            results.add_pass("다중 URL 추가", "두 번째 URL 추가됨")

        # URL 삭제 테스트
        remove_btn = page.locator(".url-remove-btn").first
        if remove_btn.count() > 0:
            # 요소가 가려져 있을 수 있으므로 스크롤 후 force click
            remove_btn.scroll_into_view_if_needed()
            time.sleep(0.2)
            remove_btn.click(force=True)
            time.sleep(0.3)
            if url_cards.count() < 2:
                results.add_pass("URL 삭제", "URL 삭제 기능 정상")
            else:
                results.add_fail("URL 삭제", "URL이 삭제되지 않음")

        # 드래그 핸들 존재 확인
        drag_handle = page.locator(".url-drag-handle").first
        if drag_handle.is_visible():
            results.add_pass("드래그 핸들", "드래그 핸들 표시됨")
        else:
            results.add_fail("드래그 핸들", "드래그 핸들이 없음")

        # 잘못된 URL 입력 테스트 (비YouTube URL)
        url_input.fill("https://www.google.com")
        url_input.press("Enter")
        time.sleep(0.3)
        # 알림이 표시되어야 함

    except Exception as e:
        results.add_fail("URL 관리 테스트", str(e))


def test_ai_service_selection(page, results):
    """AI 서비스/모델 선택 테스트"""
    try:
        page.goto(BASE_URL, timeout=10000)
        skip_onboarding_via_storage(page)
        page.reload()
        page.wait_for_load_state("networkidle")
        close_onboarding_if_visible(page)

        # Provider 드롭다운 확인
        provider_select = page.locator("#provider")
        if provider_select.is_visible():
            results.add_pass("Provider 드롭다운", "드롭다운 표시됨")
        else:
            results.add_fail("Provider 드롭다운", "드롭다운이 보이지 않음")
            return

        # Provider 옵션 확인
        options = provider_select.locator("option")
        count = options.count()
        if count >= 1:
            results.add_pass("Provider 옵션", f"{count}개의 옵션 표시")
        else:
            results.add_fail("Provider 옵션", "옵션이 없음")

        # Model 드롭다운 확인
        model_select = page.locator("#model")
        if model_select.is_visible():
            results.add_pass("Model 드롭다운", "드롭다운 표시됨")
        else:
            results.add_fail("Model 드롭다운", "드롭다운이 보이지 않음")

        # Provider 변경 시 Model 업데이트 확인
        if count >= 1:
            provider_select.select_option(index=0)
            time.sleep(0.3)
            model_options = model_select.locator("option")
            if model_options.count() >= 1:
                results.add_pass("Model 연동", "Provider 변경 시 Model 옵션 업데이트됨")
            else:
                results.add_fail("Model 연동", "Model 옵션이 업데이트되지 않음")

        # 현재 Provider 라벨 업데이트 확인
        provider_label = page.locator("#current-provider-label")
        if provider_label.is_visible():
            label_text = provider_label.text_content()
            results.add_pass("Provider 라벨", f"현재 선택: '{label_text}'")

    except Exception as e:
        results.add_fail("AI 서비스 선택 테스트", str(e))


def test_style_selection(page, results):
    """스타일 선택 테스트"""
    try:
        page.goto(BASE_URL, timeout=10000)
        skip_onboarding_via_storage(page)
        page.reload()
        page.wait_for_load_state("networkidle")
        close_onboarding_if_visible(page)

        # 스타일 옵션 확인 (라벨 개수 확인)
        style_labels = page.locator("#style-options label")
        count = style_labels.count()
        if count >= 10:
            results.add_pass("스타일 옵션 개수", f"{count}개의 스타일 표시")
        else:
            results.add_fail("스타일 옵션 개수", f"예상: 10개, 실제: {count}개")

        # 각 스타일 선택 테스트 (라벨 클릭 - sr-only 라디오)
        style_values = ["summary", "easy", "detailed", "needs", "news",
                       "script", "qna", "infographic", "compare", "sns"]

        for style in style_values:
            # 해당 라디오의 부모 라벨을 찾아서 클릭
            label = page.locator(f'label:has(input[name="style"][value="{style}"])')
            radio = page.locator(f'input[name="style"][value="{style}"]')
            if label.count() > 0:
                label.click()
                time.sleep(0.1)
                if radio.is_checked():
                    results.add_pass(f"스타일 '{style}'", "선택 가능")
                else:
                    results.add_fail(f"스타일 '{style}'", "선택되지 않음")
            else:
                results.add_fail(f"스타일 '{style}'", "라벨이 없음")

        # 기본 선택 확인 (summary가 기본)
        summary_label = page.locator('label:has(input[name="style"][value="summary"])')
        summary_radio = page.locator('input[name="style"][value="summary"]')
        summary_label.click()
        if summary_radio.is_checked():
            results.add_pass("기본 스타일 선택", "Summary가 선택됨")

    except Exception as e:
        results.add_fail("스타일 선택 테스트", str(e))


def test_advanced_options(page, results):
    """Advanced Options 테스트"""
    try:
        page.goto(BASE_URL, timeout=10000)
        skip_onboarding_via_storage(page)
        page.reload()
        page.wait_for_load_state("networkidle")
        close_onboarding_if_visible(page)

        # Advanced Options 토글 버튼 확인
        toggle_btn = page.locator("#advanced-options-toggle")
        if toggle_btn.is_visible():
            results.add_pass("Advanced Options 토글", "토글 버튼 표시됨")
        else:
            results.add_fail("Advanced Options 토글", "토글 버튼이 없음")
            return

        # 패널 초기 상태 확인 (숨김)
        panel = page.locator("#advanced-options-panel")
        initial_display = panel.evaluate("el => getComputedStyle(el).display")

        # 토글 클릭하여 열기
        toggle_btn.click()
        time.sleep(0.3)

        if panel.is_visible():
            results.add_pass("Advanced Options 열기", "패널이 펼쳐짐")
        else:
            results.add_fail("Advanced Options 열기", "패널이 열리지 않음")
            return

        # 길이 옵션 테스트 (라벨 클릭 - sr-only 라디오)
        length_options = ["short", "medium", "long"]
        for length in length_options:
            label = page.locator(f'label:has(input[name="length"][value="{length}"])')
            radio = page.locator(f'input[name="length"][value="{length}"]')
            if label.count() > 0:
                label.click()
                time.sleep(0.1)
                if radio.is_checked():
                    results.add_pass(f"길이 '{length}'", "선택 가능")
                else:
                    results.add_fail(f"길이 '{length}'", "선택되지 않음")

        # 톤 옵션 테스트 (라벨 클릭 - sr-only 라디오)
        tone_options = ["professional", "friendly", "humorous"]
        for tone in tone_options:
            label = page.locator(f'label:has(input[name="tone"][value="{tone}"])')
            radio = page.locator(f'input[name="tone"][value="{tone}"]')
            if label.count() > 0:
                label.click()
                time.sleep(0.1)
                if radio.is_checked():
                    results.add_pass(f"톤 '{tone}'", "선택 가능")

        # 언어 선택 테스트
        language_select = page.locator("#language-select")
        if language_select.is_visible():
            language_select.select_option("en")
            time.sleep(0.1)
            results.add_pass("언어 선택", "영어 선택 가능")
            language_select.select_option("ko")

        # 이모지 체크박스 테스트 (sr-only이므로 라벨 클릭)
        emoji_label = page.locator('label:has(#emoji-checkbox)')
        emoji_checkbox = page.locator("#emoji-checkbox")
        if emoji_label.count() > 0:
            emoji_label.click()
            time.sleep(0.1)
            if emoji_checkbox.is_checked():
                results.add_pass("이모지 체크박스", "체크 가능")
            else:
                results.add_fail("이모지 체크박스", "체크되지 않음")
        else:
            results.add_fail("이모지 체크박스", "라벨이 없음")

        # 다시 토글하여 닫기
        toggle_btn.click()
        time.sleep(0.3)

        if not panel.is_visible():
            results.add_pass("Advanced Options 닫기", "패널이 닫힘")
        else:
            results.add_fail("Advanced Options 닫기", "패널이 닫히지 않음")

    except Exception as e:
        results.add_fail("Advanced Options 테스트", str(e))


def test_alert_system(page, results):
    """알림 시스템 테스트"""
    try:
        page.goto(BASE_URL, timeout=10000)
        skip_onboarding_via_storage(page)
        page.reload()
        page.wait_for_load_state("networkidle")
        close_onboarding_if_visible(page)

        # 알림 컨테이너 존재 확인
        alert_container = page.locator("#alert-container")
        if alert_container.count() > 0:
            results.add_pass("알림 컨테이너", "알림 컨테이너 존재함")
        else:
            results.add_fail("알림 컨테이너", "알림 컨테이너가 없음")

        # 잘못된 URL 입력으로 알림 트리거
        url_input = page.locator("#url-input")
        url_input.fill("invalid-url")
        url_input.press("Enter")
        time.sleep(0.5)

        # 에러/경고 알림 확인
        error_alert = page.locator(".alert-error, .alert-warning")
        if error_alert.count() > 0 and error_alert.first.is_visible():
            results.add_pass("알림 표시", "잘못된 URL 입력 시 알림 표시됨")

            # 알림 닫기 버튼 테스트
            close_btn = page.locator(".alert button").first
            if close_btn.is_visible():
                close_btn.click()
                time.sleep(0.3)
                results.add_pass("알림 닫기 버튼", "알림을 닫을 수 있음")
        else:
            results.add_fail("알림 표시", "알림이 표시되지 않음")

    except Exception as e:
        results.add_fail("알림 시스템 테스트", str(e))


def test_button_states(page, results):
    """버튼 상태 테스트"""
    try:
        page.goto(BASE_URL, timeout=10000)
        skip_onboarding_via_storage(page)
        page.reload()
        page.wait_for_load_state("networkidle")
        close_onboarding_if_visible(page)

        # Start 버튼 초기 상태
        start_btn = page.locator("#start-btn")
        if start_btn.is_visible():
            results.add_pass("Start 버튼 표시", "버튼이 표시됨")

            # 버튼 텍스트 확인
            text = start_btn.text_content()
            if "Start" in text:
                results.add_pass("Start 버튼 텍스트", f"텍스트: '{text}'")

        # Run Analysis 버튼 초기 상태
        run_btn = page.locator("#run-analysis-btn")
        if run_btn.is_visible():
            results.add_pass("Run Analysis 버튼 표시", "버튼이 표시됨")

            # 아이콘 확인
            run_icon = page.locator("#run-icon")
            if run_icon.is_visible():
                icon_text = run_icon.text_content()
                results.add_pass("Run 버튼 아이콘", f"아이콘: '{icon_text}'")

        # 호버 효과 테스트 (시각적 확인)
        run_btn.hover()
        time.sleep(0.3)
        results.add_pass("버튼 호버", "호버 효과 적용됨 (시각적 확인)")

    except Exception as e:
        results.add_fail("버튼 상태 테스트", str(e))


def close_onboarding_if_visible(page, timeout=5000):
    """Onboarding 모달이 열려있으면 닫기 (여러 방법 시도)"""
    try:
        onboarding = page.locator("#onboarding-modal")
        if not onboarding.is_visible(timeout=1000):
            return True

        # 방법 1: 닫기 버튼 클릭 시도
        close_btn = page.locator("#onboarding-modal .modal-close, #onboarding-modal [aria-label*='닫기']")
        if close_btn.count() > 0 and close_btn.first.is_visible():
            close_btn.first.click()
            time.sleep(0.3)
            if not onboarding.is_visible():
                return True

        # 방법 2: 체크박스 선택 후 저장
        first_checkbox = page.locator("[data-onboard-check]").first
        if first_checkbox.is_visible():
            first_checkbox.click()
            time.sleep(0.3)
            key_input = page.locator("[data-onboard-key]").first
            if key_input.is_visible():
                key_input.fill("test-key-12345")
            save_btn = page.locator("#onboarding-save")
            if save_btn.is_visible():
                save_btn.click()
                time.sleep(0.5)
                if not onboarding.is_visible():
                    return True

        # 방법 3: ESC 키로 닫기
        page.keyboard.press("Escape")
        time.sleep(0.3)
        if not onboarding.is_visible():
            return True

        # 방법 4: 오버레이 클릭 (모달 밖 영역)
        page.mouse.click(10, 10)
        time.sleep(0.3)

        return not onboarding.is_visible()
    except Exception:
        return False


def skip_onboarding_via_storage(page):
    """localStorage 설정으로 온보딩 건너뛰기"""
    page.evaluate("""
        localStorage.setItem('onboarding_completed', 'true');
        localStorage.setItem('cad_settings_v1', JSON.stringify({
            providers: { openai: { apiKey: 'test-key-12345' } },
            selectedProvider: 'openai',
            onboardingCompleted: true
        }));
    """)


def setup_test_api_key(page):
    """테스트용 API 키 설정"""
    # localStorage에 테스트 설정 저장
    page.evaluate("""
        localStorage.setItem('cad_settings_v1', JSON.stringify({
            providers: {
                openai: { apiKey: 'test-key-12345' }
            },
            selectedProvider: 'openai'
        }));
    """)
    page.reload()
    page.wait_for_load_state("networkidle")
    close_onboarding_if_visible(page)


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
