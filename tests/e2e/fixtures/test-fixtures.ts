import { test as base, expect, Page, BrowserContext } from '@playwright/test';

/**
 * 테스트 격리를 위한 공통 Fixtures
 *
 * 병렬 테스트 원칙:
 * 1. 각 테스트는 독립적으로 실행 가능
 * 2. 테스트 간 상태 공유 없음
 * 3. 각 테스트가 자체 데이터를 생성하고 정리
 */

// ============================================
// 테스트 데이터 (격리된 샘플 데이터)
// ============================================
export const TEST_DATA = {
  // 테스트용 YouTube URL (실제 존재하는 공개 영상)
  VALID_URLS: [
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ', // Rick Astley
    'https://www.youtube.com/watch?v=jNQXAC9IVRw', // Me at the zoo
    'https://www.youtube.com/watch?v=9bZkp7q19f0', // PSY - Gangnam Style
    'https://youtu.be/kJQP7kiw5Fk', // Luis Fonsi - Despacito
    'https://www.youtube.com/watch?v=JGwWNGJdvx8', // Ed Sheeran
  ],

  // 잘못된 URL
  INVALID_URLS: [
    'not-a-url',
    'https://google.com',
    'https://vimeo.com/123456',
    'youtube.com/watch',
  ],

  // 스타일 옵션
  STYLES: [
    '상세 요약',
    '핵심 요약',
    '블로그 포스트',
    'Q&A 형식',
    '뉴스 기사',
    '교육 콘텐츠',
  ],

  // 프로바이더 (환경에 따라 다름)
  PROVIDERS: ['Gemini', 'DeepSeek', 'OpenAI', 'Claude'],
} as const;

// ============================================
// 커스텀 Fixtures 타입
// ============================================
type TestFixtures = {
  // 메인 페이지 헬퍼
  mainPage: MainPageHelper;
  // URL 입력 헬퍼
  urlInput: UrlInputHelper;
  // 콘텐츠 생성 헬퍼
  contentGenerator: ContentGeneratorHelper;
  // 인증 헬퍼
  auth: AuthHelper;
};

// ============================================
// 메인 페이지 헬퍼 클래스
// ============================================
class MainPageHelper {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');

    // 환영 모달이 있으면 닫기
    await this.dismissWelcomeModal();
  }

  async dismissWelcomeModal() {
    // 온보딩 모달이 활성화되어 있는지 확인
    const onboardingModal = this.page.locator('#onboarding-modal.active, #onboarding-modal:visible');
    const isModalVisible = await onboardingModal.isVisible().catch(() => false);

    if (isModalVisible) {
      // "시작하기" 버튼 (#onboarding-save) 클릭
      const saveButton = this.page.locator('#onboarding-save');
      if (await saveButton.isVisible().catch(() => false)) {
        await saveButton.click();
        await this.page.waitForTimeout(500);
        return;
      }

      // 또는 "먼저 둘러보기" 버튼 (#onboarding-skip) 클릭
      const skipButton = this.page.locator('#onboarding-skip');
      if (await skipButton.isVisible().catch(() => false)) {
        await skipButton.click();
        await this.page.waitForTimeout(500);
        return;
      }
    }

    // 일반 시작하기 버튼 (fallback)
    const startButton = this.page.locator('button:has-text("시작하기")');
    if (await startButton.isVisible().catch(() => false)) {
      await startButton.click();
      await this.page.waitForTimeout(500);
    }
  }

  async waitForReady() {
    // 환영 모달 먼저 닫기
    await this.dismissWelcomeModal();

    // 주요 UI 요소가 로드될 때까지 대기
    await this.page.waitForSelector('#url-input', {
      timeout: 10_000,
    });
  }

  async getProviderOptions(): Promise<string[]> {
    const options = await this.page.locator('#provider option').allTextContents();
    return options.filter(Boolean);
  }

  async getStyleOptions(): Promise<string[]> {
    // 스타일은 카드 형태로 되어 있음
    const cards = await this.page.locator('.style-card, [data-style]').allTextContents();
    return cards.filter(Boolean);
  }

  async toggleTheme() {
    await this.page.click('#theme-toggle-btn');
  }

  async getCurrentTheme(): Promise<'dark' | 'light'> {
    const html = this.page.locator('html');
    const classList = await html.getAttribute('class');
    return classList?.includes('dark') ? 'dark' : 'light';
  }
}

// ============================================
// URL 입력 헬퍼 클래스
// ============================================
class UrlInputHelper {
  constructor(private page: Page) {}

  async addUrl(url: string) {
    const input = this.page.locator('#url-input');
    // 입력 필드 클릭하여 포커스
    await input.click();
    await this.page.waitForTimeout(100);
    // URL 입력
    await input.fill(url);
    await this.page.waitForTimeout(100);
    // Enter 키로 URL 추가
    await input.press('Enter');
    // URL 카드가 추가될 때까지 대기
    await this.page.waitForTimeout(1000);
  }

  async addMultipleUrls(urls: string[]) {
    for (const url of urls) {
      await this.addUrl(url);
    }
  }

  async getUrlCount(): Promise<number> {
    // url-list-container 내의 URL 항목 수 (.url-card 클래스)
    const cards = this.page.locator('#url-list-container .url-card');
    return cards.count();
  }

  async removeUrl(index: number) {
    // JavaScript를 통해 삭제 버튼 클릭 (이벤트 리스너 직접 호출)
    const removed = await this.page.evaluate((idx) => {
      const cards = document.querySelectorAll('#url-list-container .url-card');
      if (cards.length > idx) {
        const deleteBtn = cards[idx].querySelector('.url-remove-btn') as HTMLElement;
        if (deleteBtn) {
          deleteBtn.click();
          return true;
        }
      }
      return false;
    }, index);

    if (removed) {
      await this.page.waitForTimeout(500);
    }
  }

  async clearAllUrls() {
    let count = await this.getUrlCount();
    while (count > 0) {
      await this.removeUrl(0);
      count = await this.getUrlCount();
    }
  }

  async getErrorMessage(): Promise<string | null> {
    const error = this.page.locator('.toast-error, .error-message, [role="alert"]');
    if (await error.isVisible().catch(() => false)) {
      return error.textContent();
    }
    return null;
  }
}

// ============================================
// 콘텐츠 생성 헬퍼 클래스
// ============================================
class ContentGeneratorHelper {
  constructor(private page: Page) {}

  async selectProvider(provider: string) {
    await this.page.selectOption('#provider', { label: provider });
  }

  async selectModel(model: string) {
    await this.page.selectOption('#model', { label: model });
  }

  async selectStyle(styleName: string) {
    // 스타일 카드 클릭
    const styleCard = this.page.locator(`.style-card:has-text("${styleName}"), [data-style="${styleName}"]`);
    if (await styleCard.isVisible().catch(() => false)) {
      await styleCard.click();
    }
  }

  async clickGenerate() {
    await this.page.click('#run-analysis-btn');
  }

  async waitForGenerationComplete(timeout = 60_000) {
    // 로딩이 끝나고 결과가 표시될 때까지 대기
    await this.page.waitForSelector('.result-card, #results-container .card', {
      timeout,
      state: 'visible',
    });
  }

  async isLoading(): Promise<boolean> {
    const loader = this.page.locator('.loading, .spinner, .animate-spin, [aria-busy="true"]');
    return loader.isVisible().catch(() => false);
  }

  async cancelGeneration() {
    const cancelBtn = this.page.locator('button:has-text("취소"), button:has-text("중지")');
    if (await cancelBtn.isVisible().catch(() => false)) {
      await cancelBtn.click();
    }
  }

  async getGeneratedContent(): Promise<{ title: string; content: string } | null> {
    const resultCard = this.page.locator('.result-card, #results-container .card').first();
    if (await resultCard.isVisible().catch(() => false)) {
      const title = await resultCard.locator('h2, .title, .card-title').first().textContent().catch(() => '');
      const content = await resultCard.locator('.content, .body, p').first().textContent().catch(() => '');
      return { title: title || '', content: content || '' };
    }
    return null;
  }

  async getErrorMessage(): Promise<string | null> {
    const error = this.page.locator('.toast-error, .error-message, [role="alert"]');
    if (await error.isVisible().catch(() => false)) {
      return error.textContent();
    }
    return null;
  }
}

// ============================================
// 인증 헬퍼 클래스
// ============================================
class AuthHelper {
  constructor(private page: Page) {}

  async login(email: string, password: string) {
    await this.page.goto('/login');
    await this.page.fill('[data-testid="email-input"], input[type="email"]', email);
    await this.page.fill('[data-testid="password-input"], input[type="password"]', password);
    await this.page.click('[data-testid="login-button"], button:has-text("로그인")');
    await this.page.waitForURL('/', { timeout: 10_000 });
  }

  async logout() {
    await this.page.click('[data-testid="user-menu"], .user-menu');
    await this.page.click('[data-testid="logout-button"], button:has-text("로그아웃")');
  }

  async isLoggedIn(): Promise<boolean> {
    const userMenu = this.page.locator('[data-testid="user-menu"], .user-menu');
    return userMenu.isVisible();
  }

  async saveStorageState(path: string) {
    const context = this.page.context();
    await context.storageState({ path });
  }
}

// ============================================
// Extended Test with Custom Fixtures
// ============================================
export const test = base.extend<TestFixtures>({
  mainPage: async ({ page }, use) => {
    const helper = new MainPageHelper(page);
    await use(helper);
  },

  urlInput: async ({ page }, use) => {
    const helper = new UrlInputHelper(page);
    await use(helper);
  },

  contentGenerator: async ({ page }, use) => {
    const helper = new ContentGeneratorHelper(page);
    await use(helper);
  },

  auth: async ({ page }, use) => {
    const helper = new AuthHelper(page);
    await use(helper);
  },
});

export { expect };

// ============================================
// 유틸리티 함수
// ============================================
export function getRandomUrl(): string {
  const urls = TEST_DATA.VALID_URLS;
  return urls[Math.floor(Math.random() * urls.length)];
}

export function getUniqueUrls(count: number): string[] {
  const urls = [...TEST_DATA.VALID_URLS];
  const result: string[] = [];
  for (let i = 0; i < Math.min(count, urls.length); i++) {
    const randomIndex = Math.floor(Math.random() * urls.length);
    result.push(urls.splice(randomIndex, 1)[0]);
  }
  return result;
}

export async function waitForNetworkIdle(page: Page, timeout = 5000) {
  await page.waitForLoadState('networkidle', { timeout });
}
