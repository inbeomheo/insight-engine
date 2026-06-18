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
    optimizePackageImports: ['lucide-react', 'radix-ui'],
  },
  async rewrites() {
    const backend = process.env.NEXT_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
    return [
      { source: '/api/:path*', destination: `${backend}/api/:path*` },
      { source: '/generate', destination: `${backend}/generate` },
      { source: '/generate-stream', destination: `${backend}/generate-stream` },
      { source: '/generate-batch', destination: `${backend}/generate-batch` },
      { source: '/regenerate', destination: `${backend}/regenerate` },
    ];
  },
  async headers() {
    return [{
      source: '/_next/static/:path*',
      headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }],
    }];
  },
};

export default nextConfig;
