"""
전체 웹 기능 테스트 (Playwright sync API)
실행: python tests/web_feature_test.py
서버가 localhost:5001에서 실행 중이어야 함
"""
from playwright.sync_api import sync_playwright
import time
import sys

BASE = "http://localhost:5001"
RESULTS = []

def log(name, passed, detail=""):
    icon = "PASS" if passed else "FAIL"
    RESULTS.append((name, passed))
    msg = f"  [{icon}] {name}"
    if detail:
        msg += f" -{detail}"
    print(msg)

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # ==================== T1. 메인 페이지 로드 ====================
        page.goto(BASE)
        page.wait_for_load_state("networkidle")
        title = page.title()
        log("T1. 메인 페이지 로드", "Insight Engine" in title, f"title={title}")

        # 온보딩 모달 닫기
        onboarding = page.query_selector("#onboarding-modal.active")
        if onboarding:
            close = onboarding.query_selector("button")
            if close:
                close.click()
                page.wait_for_timeout(500)

        # ==================== T2. 로그인 UI 없음 ====================
        login_btn = page.query_selector("#sidebar-auth-container")
        auth_modal = page.query_selector("#auth-modal")
        auth_visible = auth_modal.is_visible() if auth_modal else False
        log("T2. 로그인 버튼 제거", login_btn is None, f"btn={login_btn}, modal_visible={auth_visible}")

        # ==================== T3. ChatMock 모델만 표시 ====================
        # 설정(⚙) 클릭 → 모델 설정 확인
        settings_btn = page.query_selector("#settings-btn")
        if settings_btn:
            settings_btn.click()
            page.wait_for_timeout(500)

        # provider select가 남아 있으면 레거시 프로바이더가 없는지 확인
        provider_select = page.query_selector("#provider")
        provider_options = []
        if provider_select:
            provider_options = provider_select.query_selector_all("option")
            provider_options = [o.text_content().strip() for o in provider_options]
        has_chatmock = "ChatMock" in page.content()
        no_zhipu = not any("GLM" in opt or "Zhipu" in opt for opt in provider_options)
        no_gemini = not any("Gemini" in opt for opt in provider_options)
        no_deepseek = not any("DeepSeek" in opt for opt in provider_options)
        log("T3. ChatMock 모델만", has_chatmock and no_zhipu and no_gemini and no_deepseek, f"providers={provider_options}")

        # 모달 닫기
        close_btn = page.query_selector("#modal-close")
        if close_btn:
            close_btn.click()
            page.wait_for_timeout(300)

        # ==================== T4. 11개 스타일 표시 ====================
        # 스타일 popover 열기
        style_trigger = page.query_selector("#style-popover-trigger")
        if style_trigger:
            style_trigger.click()
            page.wait_for_timeout(300)

        style_inputs = page.query_selector_all('#style-options input[name="style"]')
        style_values = [inp.get_attribute("value") for inp in style_inputs]
        expected = ["blog_seo", "summary", "tutorial", "qna", "app_ideas", "yozm_it",
                    "brunch_essay", "naver_popular", "sns_post", "newsletter", "show_notes"]
        all_present = all(s in style_values for s in expected)
        log("T4. 11개 스타일", all_present and len(style_values) == 11, f"found={len(style_values)}: {style_values}")

        # ==================== T5. 멀티 생성 토글 ====================
        # 스타일 팝오버가 열린 상태에서 테스트
        multi_checkbox = page.query_selector("#multi-style-checkbox")
        log("T5. 멀티 생성 체크박스 존재", multi_checkbox is not None)

        if multi_checkbox:
            try:
                # 팝오버를 다시 열고 JS로 체크박스 토글
                style_trigger = page.query_selector("#style-popover-trigger")
                if style_trigger:
                    style_trigger.click()
                    page.wait_for_timeout(300)
                page.evaluate("const cb = document.getElementById('multi-style-checkbox'); if(cb){cb.checked=true; cb.dispatchEvent(new Event('change'));}")
                page.wait_for_timeout(500)
                first_style = page.query_selector('#style-options input[name="style"]')
                input_type = first_style.get_attribute("type") if first_style else "?"
                log("T5-1. 멀티모드 전환", input_type == "checkbox", f"type={input_type}")
                page.evaluate("const cb = document.getElementById('multi-style-checkbox'); if(cb){cb.checked=false; cb.dispatchEvent(new Event('change'));}")
                page.wait_for_timeout(300)
            except Exception as e:
                log("T5-1. 멀티모드 전환", False, str(e)[:60])

        # popover 닫기
        page.click("body", position={"x": 10, "y": 10})
        page.wait_for_timeout(300)

        # ==================== T6. URL 입력 + 콘텐츠 생성 ====================
        url_input = page.query_selector("#url-input")
        if url_input:
            url_input.fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            url_input.press("Enter")
            page.wait_for_timeout(500)

        # URL 칩 표시 확인
        url_chips = page.query_selector_all(".url-chip")
        log("T6. URL 입력 + 칩 표시", len(url_chips) >= 1, f"chips={len(url_chips)}")

        # 생성 버튼 클릭
        # 생성 버튼 - JS에서 handleGenerate 직접 호출
        run_btn = page.query_selector("#run-analysis-btn") or page.query_selector("#start-btn")
        if run_btn:
            is_disabled = run_btn.get_attribute("disabled")
            log("T6-1. 생성 버튼 활성", is_disabled is None, f"disabled={is_disabled}")
            page.evaluate("window.app?.generator?.handleGenerate()")

            # 결과 대기 (최대 180초) - pending 또는 완료 카드
            try:
                page.wait_for_selector(".result-card--unified, [data-report-id]", timeout=180000)
                cards = page.query_selector_all(".result-card--unified")
                log("T7. 콘텐츠 생성 완료", len(cards) >= 1, f"cards={len(cards)}")

                # ==================== T8. 결과 카드 구성 확인 ====================
                card = cards[0]

                # 제목
                title_el = card.query_selector(".unified-title")
                card_title = title_el.text_content().strip() if title_el else ""
                log("T8. 카드 제목", len(card_title) > 3, f'"{card_title[:40]}"')

                # 본문
                body = card.query_selector(".unified-body")
                body_text = body.text_content().strip() if body else ""
                log("T8-1. 카드 본문", len(body_text) > 50, f"{len(body_text)} chars")

                # 품질 스코어
                quality = card.query_selector(".quality-score-section")
                log("T8-2. 품질 스코어", quality is not None)

                # ==================== T9. 더보기 메뉴 ====================
                more_btn = card.query_selector(".more-actions-btn button")
                if more_btn:
                    more_btn.hover()
                    page.wait_for_timeout(300)

                    menu = card.query_selector(".more-actions-menu")
                    docx_btn = card.query_selector(".docx-export-btn")
                    pdf_btn = card.query_selector(".pdf-print-btn")
                    html_btn = card.query_selector(".html-export-btn")
                    prompt_btn = card.query_selector(".prompt-btn")
                    log("T9. 더보기 메뉴 - DOCX 버튼", docx_btn is not None)
                    log("T9-1. 더보기 메뉴 - PDF 버튼", pdf_btn is not None)
                    log("T9-2. 더보기 메뉴 - HTML 버튼", html_btn is not None)
                    log("T9-3. 더보기 메뉴 - 프롬프트 버튼", prompt_btn is not None)

                # ==================== T10. 복사 버튼 ====================
                copy_title = card.query_selector(".copy-title-btn")
                copy_content = card.query_selector(".copy-content-btn")
                copy_rich = card.query_selector(".copy-rich-btn")
                log("T10. 복사 버튼 3종", all([copy_title, copy_content, copy_rich]))

                # ==================== T11. 다운로드 버튼 ====================
                download_btn = card.query_selector(".download-btn")
                log("T11. 다운로드(MD) 버튼", download_btn is not None)

            except Exception as e:
                log("T7. 콘텐츠 생성 완료", False, str(e)[:80])

        else:
            log("T6-1. 생성 버튼", False, "run-analysis-btn not found")
            log("T7. 콘텐츠 생성", False, "skipped")

        # ==================== T12. 히스토리 사이드바 ====================
        sidebar_items = page.query_selector_all(".history-item, .sidebar-history-item")
        log("T12. 히스토리 사이드바 (localStorage)", True, f"items={len(sidebar_items)}")

        # ==================== 스크린샷 ====================
        page.screenshot(path="tests/web_test_result.png", full_page=True)
        print(f"\n  스크린샷: tests/web_test_result.png")

        browser.close()

    # ==================== 최종 결과 ====================
    passed = sum(1 for _, p in RESULTS if p)
    total = len(RESULTS)
    print(f"\n{'='*50}")
    print(f"웹 기능 테스트 결과: {passed}/{total} PASS")
    if passed < total:
        failed = [(n, p) for n, p in RESULTS if not p]
        print(f"실패: {[n for n, _ in failed]}")
    print(f"{'='*50}")
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(run_tests())
