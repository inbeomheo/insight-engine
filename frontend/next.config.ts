import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Phase 6: 프로덕션 최적화
  compress: true,
  poweredByHeader: false,
  experimental: {
    proxyTimeout: 600_000,
  },
  async headers() {
    return [{
      source: '/_next/static/:path*',
      headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }],
    }];
  },
  async rewrites() {
    return [
      { source: '/api/:path*', destination: 'http://localhost:5001/api/:path*' },
      { source: '/generate', destination: 'http://localhost:5001/generate' },
      { source: '/generate-stream', destination: 'http://localhost:5001/generate-stream' },
      { source: '/generate-batch', destination: 'http://localhost:5001/generate-batch' },
      { source: '/regenerate', destination: 'http://localhost:5001/regenerate' },
    ];
  },
};

export default nextConfig;
