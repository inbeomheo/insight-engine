// Insight Engine Chrome Extension — popup.js

const DEFAULT_SERVER = 'http://localhost:3000';

const urlDisplay = document.getElementById('url-display');
const styleSelect = document.getElementById('style-select');
const serverInput = document.getElementById('server-url');
const generateBtn = document.getElementById('generate-btn');
const statusEl = document.getElementById('status');
const openSettings = document.getElementById('open-settings');

let currentUrl = '';

// 저장된 설정 불러오기
chrome.storage.local.get(['serverUrl', 'defaultStyle'], (data) => {
  serverInput.value = data.serverUrl || DEFAULT_SERVER;
  if (data.defaultStyle) styleSelect.value = data.defaultStyle;
});

// 현재 탭 URL 감지
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  const tab = tabs[0];
  if (tab && tab.url && tab.url.includes('youtube.com/watch')) {
    currentUrl = tab.url;
    urlDisplay.textContent = currentUrl;
  } else {
    urlDisplay.textContent = 'YouTube 영상 페이지에서 사용해주세요.';
    generateBtn.disabled = true;
  }
});

// 설정 저장
openSettings.addEventListener('click', () => {
  chrome.storage.local.set({
    serverUrl: serverInput.value.trim() || DEFAULT_SERVER,
    defaultStyle: styleSelect.value,
  }, () => {
    showStatus('설정이 저장되었습니다.', false);
  });
});

// 콘텐츠 생성 요청
generateBtn.addEventListener('click', async () => {
  if (!currentUrl) return;

  const serverUrl = serverInput.value.trim() || DEFAULT_SERVER;
  const style = styleSelect.value;

  generateBtn.disabled = true;
  showStatus('생성 중...', false);

  try {
    const resp = await fetch(`${serverUrl}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        urls: [currentUrl],
        style_id: style,
        modifiers: { length: 'medium', language: 'ko' },
      }),
    });

    if (resp.ok) {
      showStatus('생성 완료! 서버에서 결과를 확인하세요.', false);
      // 결과 페이지로 이동
      chrome.tabs.create({ url: serverUrl });
    } else {
      const err = await resp.json();
      showStatus(err.error || '생성 중 오류가 발생했습니다.', true);
    }
  } catch (e) {
    showStatus(`서버 연결 실패: ${e.message}`, true);
  } finally {
    generateBtn.disabled = false;
  }
});

function showStatus(msg, isError) {
  statusEl.textContent = msg;
  statusEl.className = isError ? 'error' : '';
}
