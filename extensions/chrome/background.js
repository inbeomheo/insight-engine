/**
 * Insight Engine - Background Service Worker
 * API 호출 및 사이드패널 관리를 담당합니다.
 */

'use strict';

// 기본 서버 URL
const DEFAULT_SERVER_URL = 'http://localhost:5001';

/**
 * 저장소에서 서버 URL을 가져옵니다
 */
async function getServerUrl() {
  return new Promise((resolve) => {
    chrome.storage.sync.get({ serverUrl: DEFAULT_SERVER_URL }, (result) => {
      resolve(result.serverUrl || DEFAULT_SERVER_URL);
    });
  });
}

/**
 * 백엔드에 콘텐츠 생성 요청을 보냅니다
 * @param {string} url - YouTube URL
 * @param {string} style - 스타일 ID (blog_seo, summary 등)
 * @param {string} provider - AI 프로바이더
 * @param {string} model - AI 모델
 * @param {Object} modifiers - 모디파이어 (length, writing_style, language)
 * @returns {Promise<Object>} API 응답
 */
async function generateContent(url, style, provider, model, modifiers = {}) {
  const serverUrl = await getServerUrl();

  const body = {
    url,
    style,
    provider,
    model,
    modifiers: {
      length: modifiers.length || 'medium',
      writing_style: modifiers.writing_style || 'conversational',
      language: modifiers.language || 'ko',
    },
  };

  const response = await fetch(`${serverUrl}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(120000), // 2분 타임아웃
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.error || `서버 오류: ${response.status}`);
  }

  return response.json();
}

/**
 * 서버 연결 상태를 확인합니다
 */
async function checkConnection(serverUrl) {
  try {
    const url = serverUrl || (await getServerUrl());
    const response = await fetch(`${url}/api/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000),
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * 사용 가능한 프로바이더 목록을 가져옵니다
 */
async function getProviders() {
  try {
    const serverUrl = await getServerUrl();
    const response = await fetch(`${serverUrl}/api/providers`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return [];
    const data = await response.json();
    return data.providers || [];
  } catch {
    return [];
  }
}

// ── 메시지 핸들러 ──────────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const { action } = message;

  if (action === 'openSidePanel') {
    // 사이드패널 열기
    chrome.sidePanel
      .open({ windowId: sender.tab.windowId })
      .then(() => {
        // URL을 사이드패널로 전달하기 위해 저장
        chrome.storage.session.set({ pendingUrl: message.url });
        sendResponse({ success: true });
      })
      .catch((err) => {
        console.error('[Insight Engine] 사이드패널 열기 실패:', err);
        sendResponse({ success: false, error: err.message });
      });
    return true; // 비동기 응답
  }

  if (action === 'generateContent') {
    const { url, style, provider, model, modifiers } = message;
    generateContent(url, style, provider, model, modifiers)
      .then((data) => sendResponse({ success: true, data }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true; // 비동기 응답
  }

  if (action === 'checkConnection') {
    checkConnection(message.serverUrl)
      .then((ok) => sendResponse({ success: ok }))
      .catch(() => sendResponse({ success: false }));
    return true;
  }

  if (action === 'getProviders') {
    getProviders()
      .then((providers) => sendResponse({ success: true, providers }))
      .catch(() => sendResponse({ success: false, providers: [] }));
    return true;
  }
});

// ── 확장 프로그램 설치/업데이트 시 초기화 ──────────────────────────────────────

chrome.runtime.onInstalled.addListener(({ reason }) => {
  if (reason === 'install') {
    chrome.storage.sync.set({ serverUrl: DEFAULT_SERVER_URL });
    console.log('[Insight Engine] 설치 완료. 서버 URL:', DEFAULT_SERVER_URL);
  }
});
