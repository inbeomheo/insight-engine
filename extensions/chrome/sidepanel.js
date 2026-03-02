/**
 * Insight Engine - Side Panel Script
 * 콘텐츠 생성 UI 및 결과 표시
 */

'use strict';

// ── DOM 요소 ──────────────────────────────────────────────────────────────────
const urlInput = document.getElementById('url-input');
const styleScroll = document.getElementById('style-scroll');
const lengthSelect = document.getElementById('length-select');
const languageSelect = document.getElementById('language-select');
const generateBtn = document.getElementById('generate-btn');
const refreshBtn = document.getElementById('refresh-btn');
const settingsBtn = document.getElementById('settings-btn');

const placeholder = document.getElementById('placeholder');
const loadingEl = document.getElementById('loading');
const loadingSteps = document.getElementById('loading-steps');
const errorMsgEl = document.getElementById('error-msg');
const resultCard = document.getElementById('result-card');
const resultTitle = document.getElementById('result-title');
const resultMeta = document.getElementById('result-meta');
const resultContent = document.getElementById('result-content');
const copyBtn = document.getElementById('copy-btn');
const copyMdBtn = document.getElementById('copy-md-btn');
const regenBtn = document.getElementById('regen-btn');

// ── 상태 ──────────────────────────────────────────────────────────────────────
let selectedStyle = 'blog_seo';
let isGenerating = false;
let lastContent = '';
let lastTitle = '';

// ── 초기화 ────────────────────────────────────────────────────────────────────

async function init() {
  // 기본 스타일 불러오기
  const stored = await chrome.storage.sync.get({ defaultStyle: 'blog_seo' });
  selectedStyle = stored.defaultStyle;
  updateStyleSelection();

  // pending URL 확인 (content.js 또는 popup.js에서 설정)
  const session = await chrome.storage.session.get('pendingUrl');
  if (session.pendingUrl) {
    urlInput.value = session.pendingUrl;
    chrome.storage.session.remove('pendingUrl');
  }
}

// ── 스타일 선택 ───────────────────────────────────────────────────────────────

function updateStyleSelection() {
  styleScroll.querySelectorAll('.style-chip').forEach((chip) => {
    chip.classList.toggle('selected', chip.dataset.style === selectedStyle);
  });
}

styleScroll.addEventListener('click', (e) => {
  const chip = e.target.closest('.style-chip');
  if (!chip) return;
  selectedStyle = chip.dataset.style;
  updateStyleSelection();
});

// ── UI 상태 관리 ──────────────────────────────────────────────────────────────

function showState(state) {
  placeholder.style.display = 'none';
  loadingEl.classList.remove('visible');
  errorMsgEl.classList.remove('visible');
  resultCard.classList.remove('visible');

  if (state === 'placeholder') {
    placeholder.style.display = 'flex';
  } else if (state === 'loading') {
    loadingEl.classList.add('visible');
  } else if (state === 'error') {
    errorMsgEl.classList.add('visible');
  } else if (state === 'result') {
    resultCard.classList.add('visible');
  }
}

// ── 로딩 단계 메시지 ──────────────────────────────────────────────────────────

const LOADING_MESSAGES = [
  '자막을 추출하는 중...',
  'AI가 콘텐츠를 분석하는 중...',
  '글을 작성하는 중...',
  '마무리 정리 중...',
];

let loadingTimer = null;
let loadingStep = 0;

function startLoadingAnimation() {
  loadingStep = 0;
  updateLoadingMessage();
  loadingTimer = setInterval(() => {
    loadingStep = (loadingStep + 1) % LOADING_MESSAGES.length;
    updateLoadingMessage();
  }, 6000);
}

function updateLoadingMessage() {
  loadingSteps.innerHTML = `
    ${LOADING_MESSAGES[loadingStep]}<br>
    <span style="font-size: 10px; opacity: 0.6;">최대 2분 소요</span>
  `;
}

function stopLoadingAnimation() {
  if (loadingTimer) {
    clearInterval(loadingTimer);
    loadingTimer = null;
  }
}

// ── 결과 표시 ─────────────────────────────────────────────────────────────────

function displayResult(data) {
  lastTitle = data.title || '';
  lastContent = data.content || '';

  resultTitle.textContent = lastTitle;

  // 메타 정보 칩
  const metaItems = [];
  if (data.usage) {
    if (data.usage.total_tokens) {
      metaItems.push(`${data.usage.total_tokens.toLocaleString()} 토큰`);
    }
    if (data.usage.processing_time) {
      metaItems.push(`${data.usage.processing_time.toFixed(1)}초`);
    }
  }
  if (lastContent) {
    metaItems.push(`${lastContent.length.toLocaleString()}자`);
  }

  resultMeta.innerHTML = metaItems
    .map((item) => `<span class="meta-chip">${item}</span>`)
    .join('');

  resultContent.textContent = lastContent;
  showState('result');
}

// ── 콘텐츠 생성 ───────────────────────────────────────────────────────────────

async function generate() {
  const url = urlInput.value.trim();

  if (!url) {
    showError('YouTube URL을 입력해주세요.');
    return;
  }

  if (!url.includes('youtube.com/watch') && !url.includes('youtu.be/')) {
    showError('유효한 YouTube 영상 URL을 입력해주세요.\n예: https://www.youtube.com/watch?v=...');
    return;
  }

  if (isGenerating) return;

  isGenerating = true;
  generateBtn.disabled = true;
  generateBtn.innerHTML = '<span>⏳</span><span>생성 중...</span>';
  showState('loading');
  startLoadingAnimation();

  const modifiers = {
    length: lengthSelect.value,
    writing_style: 'conversational',
    language: languageSelect.value,
  };

  chrome.runtime.sendMessage(
    {
      action: 'generateContent',
      url,
      style: selectedStyle,
      provider: 'gemini',
      model: 'gemini/gemini-2.5-flash-lite-preview-06-17',
      modifiers,
    },
    (response) => {
      isGenerating = false;
      generateBtn.disabled = false;
      generateBtn.innerHTML = '<span>✨</span><span>콘텐츠 생성</span>';
      stopLoadingAnimation();

      if (chrome.runtime.lastError) {
        showError('서비스 워커 오류: ' + chrome.runtime.lastError.message);
        return;
      }

      if (!response || !response.success) {
        showError(response?.error || '생성 실패. 서버가 실행 중인지 확인하세요.');
        return;
      }

      displayResult(response.data);
    }
  );
}

function showError(message) {
  errorMsgEl.textContent = message;
  showState('error');
}

// ── 복사 기능 ─────────────────────────────────────────────────────────────────

function copyToClipboard(text, btn, label) {
  navigator.clipboard
    .writeText(text)
    .then(() => {
      btn.textContent = '✓ 복사됨';
      setTimeout(() => {
        btn.textContent = label;
      }, 2000);
    })
    .catch(() => {
      btn.textContent = '복사 실패';
      setTimeout(() => {
        btn.textContent = label;
      }, 2000);
    });
}

// ── 이벤트 바인딩 ─────────────────────────────────────────────────────────────

generateBtn.addEventListener('click', generate);

// Enter 키로 생성
urlInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') generate();
});

// 전체 복사 (제목 + 내용)
copyBtn.addEventListener('click', () => {
  const text = lastTitle ? `${lastTitle}\n\n${lastContent}` : lastContent;
  copyToClipboard(text, copyBtn, '📋 복사');
});

// 마크다운 복사 (내용만)
copyMdBtn.addEventListener('click', () => {
  copyToClipboard(lastContent, copyMdBtn, '📝 마크다운 복사');
});

// 재생성
regenBtn.addEventListener('click', generate);

// 새로고침 (현재 탭 URL로 교체)
refreshBtn.addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.url?.includes('youtube.com/watch')) {
    urlInput.value = tab.url;
  }
});

// 설정 (팝업 열기 또는 새 탭)
settingsBtn.addEventListener('click', () => {
  chrome.runtime.openOptionsPage?.() || chrome.tabs.create({ url: 'popup.html' });
});

// 초기화 실행
init().then(() => {
  // pending URL이 있으면 자동으로 초기 상태 표시
  if (!urlInput.value) {
    showState('placeholder');
  }
});
