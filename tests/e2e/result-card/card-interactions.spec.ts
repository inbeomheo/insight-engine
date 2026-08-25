/**
 * 결과 카드 UI 상호작용 테스트 (API 호출 없음)
 *
 * localStorage에 mock Report를 주입하여 카드 UI 기능 검증
 */
import { test, expect, makeMockReport, injectReports } from '../fixtures/test-fixtures';

test.describe('결과 카드 상호작용', () => {
  test('접기/펼치기 토글', async ({ page }) => {
    const report = makeMockReport({
      id: 'toggle-test',
      content: '접기 펼치기 테스트용 본문입니다. 마크다운 **굵게** 처리.',
    });
    await injectReports(page, [report]);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const card = page.locator('[data-report-id="toggle-test"]');
    await expect(card).toBeVisible();

    // 초기 상태: 본문 표시됨
    const prose = card.locator('.prose');
    await expect(prose).toBeVisible();

    // 접기 버튼 클릭 (aria-label '카드 접기' — 접힌 상태에선 '카드 펼치기'로 바뀜)
    const collapseBtn = card.getByRole('button', { name: '카드 접기' });
    await expect(collapseBtn).toHaveAttribute('aria-expanded', 'true');
    await collapseBtn.click();

    // 본문 숨겨짐
    await expect(prose).not.toBeVisible();

    // 다시 클릭 → 본문 표시
    const expandBtn = card.getByRole('button', { name: '카드 펼치기' });
    await expect(expandBtn).toHaveAttribute('aria-expanded', 'false');
    await expandBtn.click();
    await expect(prose).toBeVisible();
  });

  test('더보기 메뉴 열기', async ({ page }) => {
    const report = makeMockReport({ id: 'menu-test' });
    await injectReports(page, [report]);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const card = page.locator('[data-report-id="menu-test"]');
    await expect(card).toBeVisible();

    // 더보기 (⋯) 버튼 클릭 — 푸터 영역에 있음
    const moreBtn = card.getByRole('button', { name: '더보기 메뉴' });
    await moreBtn.click();

    // 메뉴 항목 확인 (학습엔진 개편 후 구성)
    await expect(page.getByRole('menuitem', { name: '제목 복사' })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: '전체 복사' })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: '프롬프트 보기' })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: '학습 노트로 저장' })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: '이벤트 추출' })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: '영상에 질문하기' })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: 'HTML 내보내기' })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: '마크다운 (.md)' })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: '삭제' })).toBeVisible();
    // 제거된 항목: 마인드맵, DOCX/PDF, 공유(메뉴 → 헤더 버튼으로 이동)
    await expect(page.getByRole('menuitem', { name: '마인드맵', exact: true })).toHaveCount(0);
    await expect(page.getByRole('menuitem', { name: 'DOCX 내보내기' })).toHaveCount(0);
    await expect(page.getByRole('menuitem', { name: 'PDF 인쇄' })).toHaveCount(0);
    await expect(page.getByRole('menuitem', { name: '공유', exact: true })).toHaveCount(0);
  });

  test('카드 삭제', async ({ page }) => {
    const report = makeMockReport({ id: 'delete-test' });
    await injectReports(page, [report]);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const card = page.locator('[data-report-id="delete-test"]');
    await expect(card).toBeVisible();

    // 더보기 메뉴 열기
    const moreBtn = card.locator('button').last();
    await moreBtn.click();

    // "삭제" 클릭
    await page.getByRole('menuitem', { name: '삭제' }).click();

    // 카드 사라짐
    await expect(card).not.toBeVisible();
  });

  test('스타일 라벨 표시', async ({ page }) => {
    // 현행 스타일은 한국어 라벨, 목록에 없는 구 스타일 ID는 원문 폴백 표시
    const quizReport = makeMockReport({ id: 'style-label-quiz', style: 'quiz' });
    const legacyReport = makeMockReport({ id: 'style-label-legacy', style: 'blog_seo' });
    await injectReports(page, [quizReport, legacyReport]);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 헤더 스타일 라벨 요소(span.signal-meta.text-primary)로 스코프 — 노트 미리보기 태그와 중복 방지
    // 현행 스타일 'quiz' → 라벨 "퀴즈" 표시
    const quizCard = page.locator('[data-report-id="style-label-quiz"]');
    await expect(quizCard).toBeVisible();
    await expect(quizCard.locator('span.signal-meta.text-primary')).toHaveText('퀴즈');

    // 구 스타일 'blog_seo' → 원문 ID 폴백 표시
    const legacyCard = page.locator('[data-report-id="style-label-legacy"]');
    await expect(legacyCard).toBeVisible();
    await expect(legacyCard.locator('span.signal-meta.text-primary')).toHaveText('blog_seo');
  });

  test('통합 뱃지 표시 (merged:true)', async ({ page }) => {
    const report = makeMockReport({
      id: 'merged-badge-test',
      merged: true,
      source_videos: [
        { url: 'https://youtube.com/watch?v=aaa', title: '영상 A', transcript_source: 'api' },
        { url: 'https://youtube.com/watch?v=bbb', title: '영상 B', transcript_source: 'api' },
      ],
    });
    await injectReports(page, [report]);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const card = page.locator('[data-report-id="merged-badge-test"]');
    await expect(card).toBeVisible();

    // "통합" 뱃지 표시
    await expect(card.getByText('통합')).toBeVisible();
  });

  test('퓨전 뱃지 표시 (isFusion:true)', async ({ page }) => {
    const report = makeMockReport({
      id: 'fusion-badge-test',
      isFusion: true,
      fusionMeta: {
        videos_analyzed: 2,
        comments_analyzed: 10,
        web_sources_found: 3,
        total_tokens: 500,
        processing_time: 5.0,
        failed_urls: [],
      },
    });
    await injectReports(page, [report]);
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const card = page.locator('[data-report-id="fusion-badge-test"]');
    await expect(card).toBeVisible();

    // "퓨전" 뱃지 표시
    await expect(card.getByText('퓨전')).toBeVisible();
  });
});
