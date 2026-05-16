'use client';

import { useEffect, useState } from 'react';
import { reportError } from '@/lib/errorReporting';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    reportError(error, { component: 'app/error.tsx', digest: error.digest });
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

        {error.digest && (
          <p className="text-xs text-muted-foreground/70 font-mono">
            오류 ID: {error.digest}
          </p>
        )}

        <div className="flex gap-2 justify-center">
          <button
            onClick={reset}
            className="px-5 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
          >
            다시 시도
          </button>
          <button
            onClick={() => window.location.reload()}
            className="px-5 py-2.5 bg-secondary text-secondary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
          >
            새로고침
          </button>
        </div>

        {process.env.NODE_ENV !== 'production' && (
          <details
            className="text-left text-xs text-muted-foreground bg-muted/40 rounded-md p-3 mt-4"
            open={showDetails}
            onToggle={(e) => setShowDetails((e.target as HTMLDetailsElement).open)}
          >
            <summary className="cursor-pointer font-medium">개발 모드: 에러 상세</summary>
            <pre className="mt-2 whitespace-pre-wrap break-words">
              {error.name}: {error.message}
              {error.stack && '\n\n' + error.stack}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}
