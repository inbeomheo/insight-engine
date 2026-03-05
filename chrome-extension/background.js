// Insight Engine Chrome Extension — background.js (Service Worker)

chrome.runtime.onInstalled.addListener(() => {
  console.log('Insight Engine 확장 프로그램이 설치되었습니다.');
});

// 컨텍스트 메뉴 생성 (YouTube 페이지에서 우클릭)
chrome.contextMenus?.create({
  id: 'insight-engine-generate',
  title: 'Insight Engine으로 콘텐츠 생성',
  contexts: ['page', 'link'],
  documentUrlPatterns: ['https://www.youtube.com/*'],
});

chrome.contextMenus?.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'insight-engine-generate') {
    chrome.action.openPopup();
  }
});
