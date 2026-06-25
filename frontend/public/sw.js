// Insight Engine — Service Worker (캐시 전략: Network-first + 오프라인 폴백)
// v5: provider 선택지를 ChatMock/GLM으로 제한하고 퓨전 댓글 분석 누락 수정
const CACHE_NAME = 'ie-cache-v5';
const OFFLINE_URL = '/';
const MAX_ENTRIES = 100;

// 정적 자산 캐싱
const PRECACHE_URLS = [
  '/',
  '/manifest.json',
  '/favicon.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// 캐시 엔트리 수 상한 유지 (오래된 것부터 삭제)
async function putWithLimit(request, response) {
  const cache = await caches.open(CACHE_NAME);
  await cache.put(request, response);
  const keys = await cache.keys();
  if (keys.length > MAX_ENTRIES) {
    await Promise.all(
      keys.slice(0, keys.length - MAX_ENTRIES).map((k) => cache.delete(k))
    );
  }
}

self.addEventListener('fetch', (event) => {
  // http/https 외의 scheme (chrome-extension 등)은 무시
  if (!event.request.url.startsWith('http')) return;

  // API 요청은 캐싱하지 않음
  if (event.request.url.includes('/api/') || event.request.url.includes('/generate')) {
    return;
  }

  // GET 요청만 캐싱
  if (event.request.method !== 'GET') return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // 동일 출처 성공 응답만 캐싱 (CDN 등 외부 리소스는 브라우저 캐시에 위임)
        if (response.ok && new URL(event.request.url).origin === self.location.origin) {
          const clone = response.clone();
          event.waitUntil(putWithLimit(event.request, clone));
        }
        return response;
      })
      .catch(() => {
        // 오프라인 폴백
        return caches.match(event.request).then((cached) => cached || caches.match(OFFLINE_URL));
      })
  );
});
