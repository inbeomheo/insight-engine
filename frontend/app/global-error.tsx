'use client';

export default function GlobalError({
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="ko">
      <body>
        <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', fontFamily: 'sans-serif' }}>
          <div style={{ textAlign: 'center', maxWidth: '400px', padding: '0 24px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '12px' }}>
              앱에 문제가 발생했습니다
            </h2>
            <p style={{ fontSize: '14px', color: '#6A6E78', marginBottom: '20px' }}>
              예상치 못한 오류가 발생했습니다. 페이지를 새로고침해주세요.
            </p>
            <button
              onClick={reset}
              style={{
                padding: '10px 20px',
                backgroundColor: '#2F54EB',
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
          </div>
        </div>
      </body>
    </html>
  );
}
