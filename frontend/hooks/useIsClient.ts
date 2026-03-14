'use client';

import { useState, useEffect } from 'react';

/** SSR/클라이언트 hydration 불일치 방지용 훅 */
export function useIsClient() {
  const [isClient, setIsClient] = useState(false);
  useEffect(() => setIsClient(true), []);
  return isClient;
}
