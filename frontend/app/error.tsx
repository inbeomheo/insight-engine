'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('페이지 에러:', error);
  }, [error]);

  return (
    <div className="flex h-screen items-center justify-center">
      <div className="text-center space-y-4 max-w-md px-6">
        <div className="w-16 h-16 mx-auto bg-destructive/10 rounded-full flex items-center justify-center">
          <span className="text-2xl">⚠️</span>
        </div>
        <h2 className="text-lg font-semibold text-foreground">문제가 발생했습니다</h2>
        <p className="text-sm text-muted-foreground">
          페이지를 불러오는 중 오류가 발생했습니다.
          <br />
          아래 버튼을 눌러 다시 시도해주세요.
        </p>
        <button
          onClick={reset}
          className="px-5 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
        >
          다시 시도
        </button>
      </div>
    </div>
  );
}
