import { describe, expect, it } from 'vitest';
import nextConfig from './next.config';

describe('공개 공유 페이지 reverse proxy', () => {
  it('Cloudflare가 프런트 포트로 들어와도 /share/:id를 백엔드로 전달한다', async () => {
    expect(typeof nextConfig.rewrites).toBe('function');
    const rewrites = await nextConfig.rewrites!();
    const rules = Array.isArray(rewrites) ? rewrites : rewrites.beforeFiles;

    expect(rules).toContainEqual({
      source: '/share/:path*',
      destination: 'http://localhost:5001/share/:path*',
    });
  });
});
