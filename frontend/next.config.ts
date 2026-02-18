import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.resolve(__dirname),
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
