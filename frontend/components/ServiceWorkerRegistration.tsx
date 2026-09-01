'use client';

import { useEffect } from 'react';

export default function ServiceWorkerRegistration() {
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return;
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // 오프라인 지원 실패가 앱 렌더링을 막지 않도록 의도적으로 무시한다.
    });
  }, []);

  return null;
}