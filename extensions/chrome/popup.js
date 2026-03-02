/**
 * Insight Engine - Popup Script
 * 설정 관리 및 상태 표시
 */

'use strict';

// DOM 요소
const serverUrlInput = document.getElementById('server-url');
const testBtn = document.getElementById('test-btn');
const saveBtn = document.getElementById('save-btn');
const saveMsgEl = document.getElementById('save-msg');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const styleGrid = document.getElementById('style-grid');
const openPanelBtn = document.getElementById('open-panel-btn');

// 현재 선택 스타일
let selectedStyle = 'blog_seo';

// ── 초기화 ────────────────────────────────────────────────────────────────────

async function init() {
  // 저장된 설정 불러오기
  const stored = await chrome.storage.sync.get({
    serverUrl: 'http://localhost:5001',
    defaultStyle: 'blog_seo',
  });

  serverUrlInput.value = stored.serverUrl;
  selectedStyle = stored.defaultStyle;
  updateStyleSelection();
}

// ── 스타일 선택 ───────────────────────────────────────────────────────────────

function updateStyleSelection() {
  styleGrid.querySelectorAll('.style-chip').forEach((chip) => {
    chip.classList.toggle('selected', chip.dataset.style === selectedStyle);
  });
}

styleGrid.addEventListener('click', (e) => {
  const chip = e.target.closest('.style-chip');
  if (!chip) return;
  selectedStyle = chip.dataset.style;
  updateStyleSelection();

  chrome.storage.sync.set({ defaultStyle: selectedStyle });
});

// ── 서버 연결 테스트 ──────────────────────────────────────────────────────────

async function testConnection() {
  const url = serverUrlInput.value.trim() || 'http://localhost:5001';

  setStatus('checking', '연결 테스트 중...');
  testBtn.disabled = true;

  chrome.runtime.sendMessage(
    { action: 'checkConnection', serverUrl: url },
    (response) => {
      testBtn.disabled = false;
      if (chrome.runtime.lastError || !response) {
        setStatus('error', '연결 실패: 서비스 워커 오류');
        return;
      }
      if (response.success) {
        setStatus('connected', `연결 성공: ${url}`);
      } else {
        setStatus('error', `연결 실패: 서버가 실행 중인지 확인하세요`);
      }
    }
  );
}

function setStatus(type, message) {
  statusDot.className = 'status-dot ' + type;
  statusText.textContent = message;
}

testBtn.addEventListener('click', testConnection);

// ── 설정 저장 ─────────────────────────────────────────────────────────────────

saveBtn.addEventListener('click', async () => {
  const url = serverUrlInput.value.trim() || 'http://localhost:5001';
  await chrome.storage.sync.set({ serverUrl: url, defaultStyle: selectedStyle });

  saveMsgEl.classList.add('visible');
  setTimeout(() => saveMsgEl.classList.remove('visible'), 2000);
});

// ── 사이드패널 열기 ───────────────────────────────────────────────────────────

openPanelBtn.addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  // YouTube 영상 페이지인 경우 URL 저장
  if (tab.url && tab.url.includes('youtube.com/watch')) {
    await chrome.storage.session.set({ pendingUrl: tab.url });
  }

  chrome.sidePanel.open({ windowId: tab.windowId }).catch(console.error);
  window.close(); // 팝업 닫기
});

// 초기화 실행
init();
