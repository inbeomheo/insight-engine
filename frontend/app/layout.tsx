import type { Metadata, Viewport } from "next";
import "./globals.css";
import Providers from "@/components/Providers";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#2F54EB",
};

export const metadata: Metadata = {
  title: "Insight Engine — AI Content Analysis",
  description: "YouTube 영상을 AI로 분석하여 고품질 콘텐츠를 생성합니다.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Insight Engine",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
        {/* CDN 폰트 비동기 로드 — 동기 <link rel="stylesheet">는 렌더 블로킹이므로
            preconnect + 스크립트 동적 삽입으로 첫 페인트에서 분리 */}
        <link rel="preconnect" href="https://cdn.jsdelivr.net" crossOrigin="anonymous" />
        <link
          rel="preload"
          as="style"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
        />
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var l=document.createElement('link');l.rel='stylesheet';l.href='https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css';document.head.appendChild(l);})();`,
          }}
        />
        <noscript>
          <link
            rel="stylesheet"
            href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
          />
        </noscript>
      </head>
      {/* 전역 문서 스크롤은 모든 폭에서 유지한다. 메인 데스크톱 셸은 자체
          h-screen/overflow-hidden + ScrollArea를 사용하지만, dashboard·notes·profile·
          deepdives 같은 독립 라우트는 body 스크롤이 유일한 세로 탐색 경로다. */}
      <body className="min-h-dvh">
        <Providers>{children}</Providers>
        {/* PWA Service Worker 등록 */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', () => {
                  navigator.serviceWorker.register('/sw.js').catch(() => {});
                });
              }
            `,
          }}
        />
      </body>
    </html>
  );
}
