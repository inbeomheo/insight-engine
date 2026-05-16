'use client';

import { useEffect } from 'react';
import { reportError } from '@/lib/errorReporting';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    reportError(error, { component: 'app/global-error.tsx', digest: error.digest });
  }, [error]);

  return (
    <html lang="ko">
      <body className="overflow-hidden h-screen">
        <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', fontFamily: 'sans-serif' }}>
          <div style={{ textAlign: 'center', maxWidth: '400px', padding: '0 24px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '12px' }}>
              앱에 문제가 발생했습니다
            </h2>
            <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px' }}>
              예상치 못한 오류가 발생했습니다. 페이지를 새로고침해주세요.
            </p>
            {error.digest && (
              <p style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '16px', fontFamily: 'monospace' }}>
                오류 ID: {error.digest}
              </p>
            )}
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
              <button
                onClick={reset}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#6366f1',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                다시 시도
              </button>
              <button
                onClick={() => window.location.reload()}
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#e5e7eb',
                  color: '#111827',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                새로고침
              </button>
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}
