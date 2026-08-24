import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Playwright는 127.0.0.1을 사용하므로 개발 번들과 HMR 요청을 명시적으로 허용한다.
  allowedDevOrigins: ['127.0.0.1'],
  // Phase 6: 프로덕션 최적화
  compress: true,
  poweredByHeader: false,
  experimental: {
    optimizePackageImports: ['lucide-react', 'radix-ui'],
  },
  async rewrites() {
    const backend = process.env.NEXT_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
    return [
      { source: '/api/:path*', destination: `${backend}/api/:path*` },
      { source: '/generate', destination: `${backend}/generate` },
      { source: '/generate-stream', destination: `${backend}/generate-stream` },
      { source: '/generate-batch', destination: `${backend}/generate-batch` },
    ];
  },
};

export default nextConfig;
