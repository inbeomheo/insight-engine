/**
 * 히스토리 및 사용량 패널 테스트
 *
 * spec: specs/04-history-usage-panels.plan.md
 *
 * 학습엔진 UI 개편(2026-08) 기준으로 재작성:
 * - 구 사이드바 dashboard/history/usage 탭(data-section)은 제거됨
 * - 히스토리 패널 = 사이드바 자체 (검색 + 날짜별 그룹 목록, components/layout/Sidebar.tsx)
 * - 대시보드 = /dashboard 별도 페이지 (사이드바 '대시보드' 링크로 이동)
 * - 사용량 지표 = /dashboard의 로컬 작업 요약 (저장된 결과/누적 토큰 등)
 *
 * 병렬 실행: ✅
 */
import type { Page } from '@playwright/test';
import { test, expect, makeMockReport, injectReports } from '../fixtures/test-fixtures';

/** 사이드바 내비게이션 스코프 (숨겨진 모바일 셸 중복 회피) */
function sidebar(page: Page) {
  return page.getByRole('navigation', { name: '사이드바 내비게이션' });
}

test.describe('히스토리 및 사용량 패널 @parallel', () => {
  // ========================================
  // Suite 1: 사이드바 내비게이션
  // ========================================
  test.describe('Suite 1: 사이드바 내비게이션', () => {
    test('TC-1.1: 대시보드 링크 클릭 시 대시보드 페이지 표시', async ({ page, mainPage }) => {
      await mainPage.goto();

      // 1. 사이드바의 대시보드 링크 클릭
      await sidebar(page).getByRole('link', { name: '대시보드' }).click();

      // Expected: /dashboard 페이지로 이동, 작업 요약 + 시스템 건강도 표시
      await expect(page).toHaveURL(/\/dashboard/);
      await expect(page.getByRole('heading', { name: '내 작업 요약' })).toBeVisible();
      await expect(page.getByText('시스템 건강도')).toBeVisible();
    });

    test('TC-1.2: 히스토리 패널에 항목 표시 및 클릭 시 활성화', async ({ page, mainPage }) => {
      // 1. mock 리포트 2건 주입 후 접속
      await injectReports(page, [
        makeMockReport({ id: 'panel-test-1', title: '첫 번째 테스트 리포트' }),
        makeMockReport({ id: 'panel-test-2', title: '두 번째 테스트 리포트' }),
      ]);
      await mainPage.goto();

      // Expected: 사이드바(=히스토리 패널)에 두 항목 모두 표시
      const itemA = sidebar(page).getByRole('button', { name: '첫 번째 테스트 리포트 히스토리 보기' });
      const itemB = sidebar(page).getByRole('button', { name: '두 번째 테스트 리포트 히스토리 보기' });
      await expect(itemA).toBeVisible();
      await expect(itemB).toBeVisible();

      // 2. 첫 번째 항목 클릭
      await itemA.click();

      // Expected: 클릭한 항목이 활성화(aria-current)되고 다른 항목은 비활성
      await expect(itemA).toHaveAttribute('aria-current', 'true');
      await expect(itemB).not.toHaveAttribute('aria-current', 'true');

      // Expected: 메인 영역의 해당 결과 카드로 이동/표시
      await expect(page.locator('[data-report-id="panel-test-1"]')).toBeVisible();
    });

    test('TC-1.3: 대시보드에서 로컬 사용량 지표 표시', async ({ page, mainPage }) => {
      // 1. 토큰 사용량이 있는 mock 리포트 2건 주입
      await injectReports(page, [
        makeMockReport({ id: 'usage-1', title: '사용량 리포트 1', usage: { total_tokens: 120 } }),
        makeMockReport({ id: 'usage-2', title: '사용량 리포트 2', usage: { total_tokens: 80 } }),
      ]);
      await mainPage.goto();

      // 2. 사이드바에서 대시보드로 이동
      await sidebar(page).getByRole('link', { name: '대시보드' }).click();
      await expect(page).toHaveURL(/\/dashboard/);

      // Expected: 저장된 결과 2개, 누적 토큰 200 (120+80) 표시
      const savedCard = page.locator('[data-slot="card"]').filter({ hasText: '저장된 결과' });
      await expect(savedCard.getByText('2개', { exact: true })).toBeVisible();

      const tokenCard = page.locator('[data-slot="card"]').filter({ hasText: '누적 토큰' });
      await expect(tokenCard.getByText('200', { exact: true })).toBeVisible();
    });
  });

  // ========================================
  // Suite 2: 페이지 전환
  // ========================================
  test.describe('Suite 2: 페이지 전환', () => {
    test('TC-2.1: 빠른 페이지 전환 시 정상 동작', async ({ page, mainPage }) => {
      await mainPage.goto();

      // 1. 홈 → 대시보드
      await sidebar(page).getByRole('link', { name: '대시보드' }).click();
      await expect(page.getByRole('heading', { name: '내 작업 요약' })).toBeVisible();

      // 2. 대시보드 → 홈
      await page.getByRole('link', { name: '홈', exact: true }).click();
      await expect(page.locator('#url-input')).toBeVisible();

      // 3. 홈 → 노트 (지식위키)
      await sidebar(page).getByRole('link', { name: '노트' }).click();
      await expect(page.getByRole('heading', { name: 'LLMWiki 홈' })).toBeVisible();

      // 4. 노트 → 홈 (이전 화면이 그대로 다시 렌더링됨)
      await page.getByRole('link', { name: '홈으로 돌아가기' }).click();
      await expect(page.locator('#url-input')).toBeVisible();
      await expect(
        page.getByRole('heading', { name: /어떤 자료를\s*콘텐츠로 만들까요\?/ })
      ).toBeVisible();
    });

    test('TC-2.2: 히스토리 활성 상태 유지', async ({ page, mainPage }) => {
      // 1. mock 리포트 주입 후 히스토리 항목 선택
      await injectReports(page, [
        makeMockReport({ id: 'active-keep-1', title: '활성 상태 테스트 리포트' }),
      ]);
      await mainPage.goto();

      const item = sidebar(page).getByRole('button', { name: '활성 상태 테스트 리포트 히스토리 보기' });
      await item.click();
      await expect(item).toHaveAttribute('aria-current', 'true');

      // 2. 페이지 내 다른 동작 수행 (스크롤 + 히스토리 검색)
      await page.evaluate(() => window.scrollTo(0, 100));
      await sidebar(page).getByPlaceholder('히스토리 검색...').fill('활성');
      await page.waitForTimeout(500); // 검색 디바운스(200ms) 대기

      // 3. 검색 결과에도 항목이 남아있고 활성 상태 유지됨
      await expect(item).toBeVisible();
      await expect(item).toHaveAttribute('aria-current', 'true');
    });
  });
});
