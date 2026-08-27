import { test as base, expect, Page } from '@playwright/test';

// ============================================
// 테스트 데이터
// ============================================
export const TEST_DATA = {
  // 짧은 영상 (비용 최소화)
  SHORT_VIDEO: 'https://www.youtube.com/watch?v=jNQXAC9IVRw', // Me at the zoo (19초)

  VALID_URLS: [
    'https://www.youtube.com/watch?v=jNQXAC9IVRw',
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'https://www.youtube.com/watch?v=9bZkp7q19f0',
    'https://youtu.be/kJQP7kiw5Fk',
    'https://www.youtube.com/watch?v=JGwWNGJdvx8',
  ],

  // 현재 검증 규칙(^https?:\/\/)상 무효한 입력들 — 스킴 없는 URL/비 http(s) 스킴
  // (구 UI와 달리 웹페이지/RSS/arXiv/Podcast URL은 이제 전부 유효함)
  INVALID_URLS: [
    'not-a-url',
    'youtube.com/watch?v=jNQXAC9IVRw', // http(s) 스킴 없음
    'ftp://example.com/feed.xml', // http/https 아님
  ],

  // 무효 URL 입력 시 표시되는 에러 메시지 패턴
  INVALID_URL_ERROR: /유효한 URL이 아닙니다/,

  // 저비용 프리셋 (API 테스트용)
  CHEAP_PRESET: {
    provider: 'chatmock',
    model: 'chatmock/gpt-5.4-mini',
    style: 'summary',
    length: 'short' as const,
  },
} as const;

// ============================================
// 커스텀 Fixtures 타입
// ============================================
type TestFixtures = {
  mainPage: MainPageHelper;
  urlInput: UrlInputHelper;
  contentGenerator: ContentGeneratorHelper;
};

// ============================================
// 메인 페이지 헬퍼
// ============================================
class MainPageHelper {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
    await this.dismissOnboarding();
  }

  /** 온보딩 모달이 보이면 모델 유무에 따라 시작하거나 영속적으로 닫는다. */
  async dismissOnboarding() {
    const startBtn = this.page.getByRole('button', { name: '시작하기' });
    // 온보딩 모달 표시까지 잠시 대기
    const visible = await startBtn.isVisible().catch(() => false);
    if (visible) {
      if (await startBtn.isEnabled()) {
        await startBtn.click();
      } else {
        // 모델 로드 실패 시 Start는 의도적으로 disabled다. Esc도 동일한
        // onOpenChange(false) → dismiss 경로를 타며 완료 상태를 저장한다.
        await this.page.keyboard.press('Escape');
      }
      // 모달 닫힘 대기
      await startBtn.waitFor({ state: 'hidden', timeout: 3000 }).catch(() => {});
    }
  }

  /** URL 입력 필드가 준비될 때까지 대기 */
  async waitForReady() {
    await this.dismissOnboarding();
    await this.page.locator('#url-input').waitFor({ state: 'visible', timeout: 10_000 });
  }
}

// ============================================
// URL 입력 헬퍼
// ============================================
class UrlInputHelper {
  constructor(private page: Page) {}

  /** URL 추가 (입력 후 Enter) */
  async addUrl(url: string) {
    const input = this.page.locator('#url-input');
    await input.click();
    await input.fill(url);
    await input.press('Enter');
    // URL 칩 표시 대기
    await this.page.waitForTimeout(500);
  }

  /** 여러 URL 순차 추가 */
  async addMultipleUrls(urls: string[]) {
    for (const url of urls) {
      await this.addUrl(url);
    }
  }

  /** 현재 URL 칩 개수 (숨겨진 모바일 셸 중복 제외) */
  async getUrlChipCount(): Promise<number> {
    // Badge (칩) 컴포넌트 안의 X 버튼 개수로 판단
    return this.page.locator('[aria-label$="제거"]:visible').count();
  }

  /** 특정 URL 칩 삭제 (인덱스 기반) */
  async removeUrlByIndex(index: number) {
    const removeButtons = this.page.locator('[aria-label$="제거"]:visible');
    const count = await removeButtons.count();
    if (index < count) {
      await removeButtons.nth(index).click();
      await this.page.waitForTimeout(300);
    }
  }
}

// ============================================
// 콘텐츠 생성 헬퍼
// ============================================
class ContentGeneratorHelper {
  constructor(private page: Page) {}

  /** 설정 팝오버 (role=dialog, aria-label="생성 설정") */
  private settingsPopover() {
    return this.page.getByRole('dialog', { name: '생성 설정' });
  }

  /** 설정 팝오버 열기 */
  async openSettings() {
    const settingsBtn = this.page.getByRole('button', { name: '생성 설정 열기' });
    await settingsBtn.click();
    // 팝오버 렌더링 대기
    await this.settingsPopover().waitFor({ state: 'visible', timeout: 3000 });
  }

  /** 설정 팝오버 닫기 (ESC) */
  async closeSettings() {
    await this.page.keyboard.press('Escape');
    await this.page.waitForTimeout(200);
  }

  /** 저비용 프리셋 적용 (ChatMock Mini, 요약, 짧게) */
  async applyCheapPreset() {
    await this.openSettings();
    const popover = this.settingsPopover();

    // 모델 선택 (ChatMock 단일 서비스)
    const modelTrigger = popover.locator('[role="combobox"]').first();
    await modelTrigger.click();
    const options = this.page.getByRole('option');
    await options.first().waitFor({ state: 'visible', timeout: 3000 }).catch(() => {});
    const miniOption = options.filter({ hasText: /Mini/i }).first();
    if (await miniOption.isVisible().catch(() => false)) {
      await miniOption.click();
    }

    // Select 옵션이 포털에 렌더되어 옵션 클릭이 외부 클릭으로 인식됨 → 팝오버가 닫히면 재오픈
    if (!(await popover.isVisible().catch(() => false))) {
      await this.openSettings();
    }

    // 스타일: 요약 (팝오버 내부 aria-label 기준)
    await popover.getByRole('button', { name: /^요약 스타일 선택/ }).click();

    // 길이: 짧게
    await popover.getByRole('button', { name: '짧게 길이 선택' }).click();

    await this.closeSettings();
  }

  /** 생성 CTA 버튼 클릭 (모드에 따라: 콘텐츠 생성/통합 생성/퓨전 분석 — 숨겨진 모바일 CTA 제외) */
  async clickGenerate() {
    const btn = this.page
      .getByRole('button', { name: /콘텐츠 생성|통합 생성|퓨전 분석/ })
      .filter({ visible: true })
      .first();
    await btn.click();
  }

  /** 특정 모드의 생성 CTA 버튼 클릭 */
  async clickGenerateByMode(mode: 'individual' | 'combined' | 'fusion') {
    const patterns: Record<string, RegExp> = {
      individual: /콘텐츠 생성/,
      combined: /통합 생성/,
      fusion: /퓨전 분석/,
    };
    const btn = this.page
      .getByRole('button', { name: patterns[mode] })
      .filter({ visible: true })
      .first();
    await btn.click();
  }

  /** 생성 완료 대기 (결과 카드 표시) */
  async waitForResult(timeout = 180_000): Promise<void> {
    await this.page.locator('[data-report-id]').first().waitFor({
      state: 'visible',
      timeout,
    });
  }

  /** 결과 카드 개수 */
  async getResultCount(): Promise<number> {
    return this.page.locator('[data-report-id]').count();
  }

  /** 로딩 중인지 확인 (LoadingSkeleton: aria-label="콘텐츠 생성 중") */
  async isLoading(): Promise<boolean> {
    const skeleton = this.page.getByLabel('콘텐츠 생성 중').first();
    return skeleton.isVisible().catch(() => false);
  }

  /** 생성 모드 선택 (개별/통합/퓨전 — 숨겨진 모바일 버튼 제외) */
  async selectMode(mode: 'individual' | 'combined' | 'fusion') {
    const labels: Record<string, string> = {
      individual: '개별',
      combined: '통합',
      fusion: '퓨전',
    };
    await this.page
      .getByRole('button', { name: labels[mode], exact: true })
      .filter({ visible: true })
      .first()
      .click();
  }
}

// ============================================
// Fixtures 확장
// ============================================
export const test = base.extend<TestFixtures>({
  mainPage: async ({ page }, use) => {
    await use(new MainPageHelper(page));
  },
  urlInput: async ({ page }, use) => {
    await use(new UrlInputHelper(page));
  },
  contentGenerator: async ({ page }, use) => {
    await use(new ContentGeneratorHelper(page));
  },
});

export { expect };

// ============================================
// 유틸리티: localStorage에 mock Report 주입
// ============================================
export function makeMockReport(overrides: Record<string, unknown> = {}) {
  return {
    id: `test-${Date.now()}`,
    url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw',
    youtube_title: 'Test Video',
    title: '테스트 제목',
    content: '테스트 본문 내용입니다.',
    html: '<p>테스트 본문 내용입니다.</p>',
    style: 'summary',
    prompt: 'test prompt',
    usage: { total_tokens: 100 },
    elapsed_time: 1.5,
    transcript_source: 'youtube_api',
    cached: false,
    comment_summary_included: false,
    time: new Date().toLocaleString('ko-KR'),
    createdAt: Date.now(),
    ...overrides,
  };
}

/** 테스트 전에 localStorage에 mock 리포트 주입 */
export async function injectReports(page: Page, reports: Record<string, unknown>[]) {
  await page.addInitScript((data) => {
    localStorage.setItem('insight-engine-reports', JSON.stringify(data));
    // 온보딩 완료 처리
    localStorage.setItem('insight-engine-onboarding-done', 'true');
  }, reports);
}
