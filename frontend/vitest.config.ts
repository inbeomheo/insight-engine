import { defineConfig } from 'vitest/config';

// tsconfig의 paths(@/* → ./*)를 Vite 네이티브 기능으로 재사용 (별칭 중복 정의 회피)
export default defineConfig({
  resolve: {
    tsconfigPaths: true,
  },
  test: {
    environment: 'jsdom',
    include: ['**/*.test.ts', '**/*.test.tsx'],
    // E2E(Playwright)는 별도 러너이므로 제외
    exclude: ['node_modules/**', '.next/**', 'tests/e2e/**'],
  },
});
