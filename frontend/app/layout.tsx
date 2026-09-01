import type { Metadata, Viewport } from "next";
import "./globals.css";
import Providers from "@/components/Providers";
import ServiceWorkerRegistration from "@/components/ServiceWorkerRegistration";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
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
      <body>
        <Providers>{children}</Providers>
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}
