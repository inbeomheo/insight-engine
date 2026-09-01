import type { NextConfig } from "next";
import path from "path";

const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "form-action 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "worker-src 'self' blob:",
  "manifest-src 'self'",
  "upgrade-insecure-requests",
].join('; ');

const securityHeaders = [
  { key: 'Content-Security-Policy', value: contentSecurityPolicy },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), payment=()' },
  { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
];

const nextConfig: NextConfig = {
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Phase 6: 프로덕션 최적화
  compress: true,
  poweredByHeader: false,
  experimental: {
    optimizePackageImports: ['lucide-react', 'radix-ui'],
    // AI 생성은 모델 추론에 30초 이상 걸릴 수 있으므로 Next rewrite의
    // 기본 30초 upstream 제한을 브라우저/백엔드 제한과 동일하게 맞춘다.
    proxyTimeout: 300_000,
  },
  async headers() {
    return [{ source: '/:path*', headers: securityHeaders }];
  },
  async rewrites() {
    const backend = process.env.NEXT_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
    return [
      { source: '/api/:path*', destination: `${backend}/api/:path*` },
      { source: '/share/:path*', destination: `${backend}/share/:path*` },
      { source: '/generate', destination: `${backend}/generate` },
      { source: '/generate-stream', destination: `${backend}/generate-stream` },
      { source: '/generate-batch', destination: `${backend}/generate-batch` },
    ];
  },
};

export default nextConfig;
