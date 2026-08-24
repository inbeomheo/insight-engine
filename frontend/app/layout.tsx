import type { Metadata, Viewport } from "next";
import "./globals.css";
import Providers from "@/components/Providers";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
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
      {/* 데스크톱(xl+)은 내부 ScrollArea가 스크롤을 담당하므로 body를 고정 높이로 잠근다.
          그 미만(모바일/태블릿)은 문서 흐름 그대로 스크롤돼야 한다 — 잠그면 첫 화면 아래
          콘텐츠(스타일 선택·생성 모드·생성 버튼·라이브러리 카드)가 잘려 접근이 불가능해진다. */}
      <body className="min-h-dvh xl:h-screen xl:overflow-hidden">
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
