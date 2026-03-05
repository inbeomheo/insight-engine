// Insight Engine Chrome Extension — content.js
// YouTube 페이지에서 영상 URL 및 메타데이터를 추출합니다.

(function () {
  'use strict';

  /**
   * 현재 YouTube 영상 URL 반환
   */
  function getCurrentVideoUrl() {
    const url = window.location.href;
    if (url.includes('youtube.com/watch')) return url;
    return null;
  }

  /**
   * 영상 제목 추출
   */
  function getVideoTitle() {
    const titleEl = document.querySelector('h1.ytd-watch-metadata yt-formatted-string');
    return titleEl ? titleEl.textContent.trim() : document.title;
  }

  // 팝업에서 메시지 수신
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'GET_VIDEO_INFO') {
      sendResponse({
        url: getCurrentVideoUrl(),
        title: getVideoTitle(),
        pageUrl: window.location.href,
      });
    }
  });
})();
