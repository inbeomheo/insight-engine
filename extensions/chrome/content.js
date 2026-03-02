/**
 * Insight Engine - YouTube Content Script
 * YouTube 영상 페이지에 "콘텐츠 생성" 버튼을 삽입합니다.
 */

(function () {
  'use strict';

  // 이미 삽입된 경우 중복 실행 방지
  if (document.getElementById('insight-engine-btn')) return;

  let injected = false;

  /**
   * 현재 YouTube 영상 URL을 가져옵니다
   */
  function getCurrentVideoUrl() {
    return window.location.href;
  }

  /**
   * 토스트 알림을 표시합니다
   */
  function showToast(message, duration = 3000) {
    const existing = document.getElementById('insight-engine-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'insight-engine-toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
      if (toast.parentNode) toast.remove();
    }, duration);
  }

  /**
   * 사이드패널을 열고 현재 URL을 전달합니다
   */
  function openSidePanel() {
    const url = getCurrentVideoUrl();
    chrome.runtime.sendMessage(
      { action: 'openSidePanel', url },
      (response) => {
        if (chrome.runtime.lastError) {
          showToast('⚠️ 사이드패널을 열 수 없습니다. 확장 프로그램을 다시 로드해주세요.');
          return;
        }
        if (response && response.success) {
          showToast('✨ Insight Engine이 열렸습니다!');
        }
      }
    );
  }

  /**
   * YouTube 플레이어 아래의 버튼 영역에 버튼을 삽입합니다
   */
  function injectButton() {
    if (injected || document.getElementById('insight-engine-btn')) return;

    // YouTube 버튼 컨테이너 탐색 (좋아요/싫어요/공유 버튼 영역)
    const selectors = [
      '#top-level-buttons-computed',
      'ytd-video-primary-info-renderer #menu',
      '#info-contents #menu-container',
      '#actions',
    ];

    let container = null;
    for (const sel of selectors) {
      container = document.querySelector(sel);
      if (container) break;
    }

    if (!container) return;

    const btn = document.createElement('button');
    btn.id = 'insight-engine-btn';
    btn.innerHTML = '<span class="ie-icon">✨</span><span>콘텐츠 생성</span>';
    btn.title = 'Insight Engine으로 콘텐츠 생성';
    btn.addEventListener('click', openSidePanel);

    container.appendChild(btn);
    injected = true;
  }

  /**
   * URL 변경 감지 (YouTube SPA 네비게이션 대응)
   */
  function onNavigate() {
    injected = false;
    const existing = document.getElementById('insight-engine-btn');
    if (existing) existing.remove();

    // YouTube는 SPA이므로 DOM 로드 후 삽입 대기
    setTimeout(tryInject, 1500);
  }

  /**
   * 삽입 시도 (DOM 준비 대기 포함)
   */
  function tryInject(retries = 5) {
    if (!window.location.href.includes('/watch')) return;

    injectButton();

    if (!injected && retries > 0) {
      setTimeout(() => tryInject(retries - 1), 800);
    }
  }

  // 초기 실행
  tryInject();

  // YouTube SPA 네비게이션 감지
  let lastUrl = window.location.href;
  const observer = new MutationObserver(() => {
    const currentUrl = window.location.href;
    if (currentUrl !== lastUrl) {
      lastUrl = currentUrl;
      onNavigate();
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });

  // URL 변경 이벤트도 추가 감지
  window.addEventListener('yt-navigate-finish', onNavigate);
})();
