import { test, expect, TEST_DATA, injectReports, makeMockReport } from '../fixtures/test-fixtures';

/**
 * Phase 2: 핵심 사용자 흐름 E2E
 * 단일 생성, 결과 카드, 사이드바 히스토리
 */

test.describe('핵심 사용자 흐름', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  // --- 2-1. URL 입력 → 생성 버튼 활성화 ---

  test('URL 없으면 생성 버튼이 비활성화되어 있다', async ({ page }) => {
    // 새 UI: CTA는 항상 보이지만 URL이 없으면 disabled
    const genBtn = page
      .getByRole('button', { name: /콘텐츠 생성/ })
      .filter({ visible: true })
      .first();
    await expect(genBtn).toBeVisible();
    await expect(genBtn).toBeDisabled();
  });

  test('URL 입력 후 생성 버튼이 활성화된다', async ({ page }) => {
    const input = page.locator('#url-input');
    await input.fill(TEST_DATA.VALID_URLS[0]);
    await input.press('Enter');
    await page.waitForTimeout(500);

    // CTA에 URL 개수(×1)가 표시되고 활성화됨
    const genBtn = page
      .getByRole('button', { name: /콘텐츠 생성 ×1/ })
      .filter({ visible: true })
      .first();
    await expect(genBtn).toBeVisible();
    await expect(genBtn).toBeEnabled();
  });

  test('URL 입력 + Enter로 칩이 추가되고 입력이 초기화된다', async ({ page }) => {
    const input = page.locator('#url-input');
    await input.fill(TEST_DATA.VALID_URLS[0]);
    await input.press('Enter');
    await page.waitForTimeout(500);

    // 칩에 videoId가 표시됨 (VALID_URLS[0] = jNQXAC9IVRw, 전체 URL 표시 요소와 구분 위해 exact)
    await expect(page.getByText('jNQXAC9IVRw', { exact: true })).toBeVisible();
    // 칩에 제거 버튼이 함께 표시됨
    await expect(page.getByRole('button', { name: 'jNQXAC9IVRw 제거' })).toBeVisible();
    // 입력 필드가 비워짐
    await expect(input).toHaveValue('');
  });

  test('잘못된 URL 입력 시 에러 메시지가 표시된다', async ({ page }) => {
    const input = page.locator('#url-input');
    // 새 검증 규칙: http(s) 스킴 없는 입력만 무효 (웹페이지/RSS 등은 유효)
    await input.fill(TEST_DATA.INVALID_URLS[0]);
    await input.press('Enter');
    await page.waitForTimeout(300);

    await expect(page.getByText(TEST_DATA.INVALID_URL_ERROR)).toBeVisible();
    // 칩은 추가되지 않음
    await expect(page.locator('[aria-label$="제거"]')).toHaveCount(0);
  });

  test('URL X 버튼 클릭으로 칩이 삭제된다', async ({ page }) => {
    const input = page.locator('#url-input');
    await input.fill(TEST_DATA.VALID_URLS[0]);
    await input.press('Enter');
    await page.waitForTimeout(500);

    // X 버튼 클릭 (aria-label: "<videoId> 제거")
    const removeBtn = page.getByRole('button', { name: 'jNQXAC9IVRw 제거' });
    await removeBtn.click();
    await page.waitForTimeout(300);

    await expect(page.getByText('jNQXAC9IVRw', { exact: true })).not.toBeVisible();
  });

  // --- 2-2. 빈 상태 ---

  test('결과 없을 때 빈 상태 안내가 표시된다', async ({ page }) => {
    await expect(
      page.getByRole('heading', { name: '영상·텍스트·PDF를 분석해보세요' }),
    ).toBeVisible();
  });

  // --- 2-3. 온보딩 모달 ---

  test('첫 방문 시 온보딩 모달이 표시되고 시작하기로 닫을 수 있다', async ({ page }) => {
    // 새 컨텍스트로 localStorage 초기화
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.waitForLoadState('networkidle');

    // 온보딩 모달 (dialog 접근성 이름 = "환영합니다!")
    const dialog = page.getByRole('dialog', { name: '환영합니다!' });
    await expect(dialog).toBeVisible();
    // 제목 확인 (VisuallyHidden 중복 제목이 있어 first 사용)
    await expect(dialog.getByRole('heading', { name: '환영합니다!' }).first()).toBeVisible();

    await dialog.getByRole('button', { name: '시작하기' }).click();
    await expect(dialog).not.toBeVisible();
  });

  // --- 2-4. 사이드바 ---

  test('사이드바에 "새 분석" 버튼이 있다', async ({ page }) => {
    await expect(page.getByRole('button', { name: /새 분석/ })).toBeVisible();
  });

  test('사이드바 히스토리 검색이 동작한다', async ({ page, mainPage }) => {
    await injectReports(page, [
      makeMockReport({ id: 'search-match', title: '검색할 학습 노트' }),
      makeMockReport({ id: 'search-other', title: '다른 영상 요약' }),
    ]);
    await mainPage.goto();
    const sidebar = page.getByRole('navigation', { name: '사이드바 내비게이션' });
    const searchInput = page.getByPlaceholder('히스토리 검색...');
    await expect(sidebar.getByRole('button', { name: '다른 영상 요약 히스토리 보기' })).toBeVisible();
    await searchInput.fill('학습');
    await expect(sidebar.getByRole('button', { name: '검색할 학습 노트 히스토리 보기' })).toBeVisible();
    await expect(sidebar.getByRole('button', { name: '다른 영상 요약 히스토리 보기' })).toHaveCount(0);
    await searchInput.fill('');
    await expect(sidebar.getByRole('button', { name: '다른 영상 요약 히스토리 보기' })).toBeVisible();
  });

  // --- 2-5. 헤더 ---

  test('헤더에 주요 탭과 설정 버튼이 있다', async ({ page }) => {
    // 새 UI: 로고 텍스트 대신 생성/라이브러리/대시보드 탭 + 설정 버튼
    const header = page.getByRole('banner');
    await expect(header.getByRole('button', { name: '생성', exact: true })).toBeVisible();
    await expect(header.getByRole('button', { name: '라이브러리', exact: true })).toBeVisible();
    await expect(header.getByRole('button', { name: '대시보드', exact: true })).toBeVisible();
    await expect(header.getByRole('button', { name: '설정 열기', exact: true })).toBeVisible();
  });

  // --- 2-6. 설정 ---

  test('설정 버튼 클릭 시 설정 모달이 열린다', async ({ page }) => {
    await page.getByRole('button', { name: '설정 열기', exact: true }).click();
    await page.waitForTimeout(500);

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
  });
});

test.describe('다중 URL 모드', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('URL 2개 추가 시 통합/퓨전 모드를 선택할 수 있다', async ({ page }) => {
    const input = page.locator('#url-input');

    await input.fill(TEST_DATA.VALID_URLS[0]);
    await input.press('Enter');
    await page.waitForTimeout(500);

    await input.fill(TEST_DATA.VALID_URLS[1]);
    await input.press('Enter');
    await page.waitForTimeout(500);

    // 모드 버튼 (개별/통합/퓨전)이 표시됨 — 숨겨진 모바일 버튼 제외
    for (const label of ['개별', '통합', '퓨전']) {
      await expect(
        page.getByRole('button', { name: label, exact: true }).filter({ visible: true }).first(),
      ).toBeVisible();
    }

    // 통합 모드 선택 → 통합 생성 CTA가 활성화됨 (URL 2개)
    await page
      .getByRole('button', { name: '통합', exact: true })
      .filter({ visible: true })
      .first()
      .click();
    const mergedBtn = page
      .getByRole('button', { name: /통합 생성 ×2/ })
      .filter({ visible: true })
      .first();
    await expect(mergedBtn).toBeEnabled();
  });

  test('최대 10개 URL 제한이 적용된다', async ({ page }) => {
    const input = page.locator('#url-input');

    // 5개 유효 URL 추가
    for (const url of TEST_DATA.VALID_URLS) {
      await input.fill(url);
      await input.press('Enter');
      await page.waitForTimeout(300);
    }

    // 추가로 5개 더 (다른 URL 사용)
    const extraUrls = [
      'https://www.youtube.com/watch?v=L_jWHffIx5E',
      'https://www.youtube.com/watch?v=fJ9rUzIMcZQ',
      'https://www.youtube.com/watch?v=YQHsXMglC9A',
      'https://www.youtube.com/watch?v=hT_nvWreIhg',
      'https://www.youtube.com/watch?v=RgKAFK5djSk',
    ];
    for (const url of extraUrls) {
      await input.fill(url);
      await input.press('Enter');
      await page.waitForTimeout(300);
    }

    // 11번째 URL 추가 시도
    await input.fill('https://www.youtube.com/watch?v=EXTRA11');
    await input.press('Enter');
    await page.waitForTimeout(300);

    // 최대 제한 에러 메시지
    await expect(page.getByText(/최대 10개/)).toBeVisible();
  });
});
