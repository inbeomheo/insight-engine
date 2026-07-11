import { ImageResponse } from 'next/og';
import { NextRequest } from 'next/server';

/**
 * OG 이미지 생성 엔드포인트
 * GET /api/og?title=...&description=...
 */
export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const title = searchParams.get('title') || 'Insight Engine';
  const description = searchParams.get('description') || 'AI 콘텐츠 생성기';

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '60px',
          background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%)',
          color: '#f8fafc',
          fontFamily: 'sans-serif',
        }}
      >
        {/* 로고/브랜드 */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            marginBottom: '32px',
            fontSize: '24px',
            color: '#94a3b8',
          }}
        >
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '20px',
            }}
          >
            ✦
          </div>
          Insight Engine
        </div>

        {/* 제목 */}
        <div
          style={{
            fontSize: title.length > 40 ? '40px' : '52px',
            fontWeight: 700,
            lineHeight: 1.2,
            marginBottom: '20px',
            display: '-webkit-box',
            overflow: 'hidden',
          }}
        >
          {title.slice(0, 80)}
        </div>

        {/* 설명 */}
        <div
          style={{
            fontSize: '24px',
            color: '#94a3b8',
            lineHeight: 1.4,
          }}
        >
          {description.slice(0, 120)}
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    },
  );
}
