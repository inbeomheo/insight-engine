/**
 * 설정 UI 검증 테스트 (API 호출 없음)
 *
 * SettingsPopover의 프로바이더/스타일/길이/문체 선택 UI 검증
 */
import { test, expect } from '../fixtures/test-fixtures';

test.describe('설정 UI (SettingsPopover)', () => {
  test.beforeEach(async ({ mainPage, contentGenerator }) => {
    await mainPage.goto();
    await contentGenerator.openSettings();
  });

  test('설정 팝오버 열기/닫기', async ({ page, contentGenerator }) => {
    // 이미 beforeEach에서 열려있음
    await expect(page.getByText('AI 모델')).toBeVisible();
    await expect(page.getByText('스타일')).toBeVisible();
    await expect(page.getByText('길이')).toBeVisible();
    await expect(page.getByText('문체')).toBeVisible();

    // 닫기 (외부 클릭)
    await contentGenerator.closeSettings();
    await expect(page.getByText('AI 모델')).not.toBeVisible();
  });

  test('프로바이더 선택 → 모델 목록 변경', async ({ page, contentGenerator }) => {
    // 프로바이더/모델 Select 트리거 (2개)
    const triggers = page.locator('[role="combobox"]');
    const triggerCount = await triggers.count();
    expect(triggerCount).toBeGreaterThanOrEqual(2);

    // 프로바이더 드롭다운 열기
    await triggers.first().click();

    // 프로바이더 옵션이 1개 이상 존재
    const options = page.getByRole('option');
    const count = await options.count();
    expect(count).toBeGreaterThanOrEqual(1);

    // 첫 번째 옵션 선택 (포탈 클릭으로 팝오버가 닫힐 수 있음)
    await options.first().click();

    // 팝오버가 닫혔으면 다시 열기
    const aiModelLabel = page.getByText('AI 모델');
    if (!await aiModelLabel.isVisible().catch(() => false)) {
      await contentGenerator.openSettings();
    }

    // 모델 Select 트리거 존재 확인
    const modelTrigger = page.locator('[role="combobox"]').nth(1);
    await expect(modelTrigger).toBeVisible();
  });

  test('11개 내장 스타일 버튼 표시', async ({ page }) => {
    const expectedStyles = [
      'Blog+SEO', '요약', '튜토리얼', 'Q&A', '앱 아이디어',
      '요즘IT', '브런치', '네이버', 'SNS', '뉴스레터', '쇼노트',
    ];

    for (const label of expectedStyles) {
      const btn = page.locator('button').filter({ hasText: label });
      await expect(btn.first()).toBeVisible();
    }
  });

  test('스타일 선택 토글', async ({ page }) => {
    // "요약" 버튼 클릭
    const summaryBtn = page.locator('button').filter({ hasText: '요약' }).first();
    await summaryBtn.click();

    // 선택된 스타일은 primary 배경
    await expect(summaryBtn).toHaveClass(/bg-primary/);

    // 다른 스타일 클릭 시 이전 선택 해제
    const tutorialBtn = page.locator('button').filter({ hasText: '튜토리얼' }).first();
    await tutorialBtn.click();

    await expect(tutorialBtn).toHaveClass(/bg-primary/);
    await expect(summaryBtn).not.toHaveClass(/bg-primary/);
  });

  test('길이 옵션 3개 (짧게/보통/길게)', async ({ page }) => {
    const lengths = ['짧게', '보통', '길게'];

    for (const label of lengths) {
      const btn = page.locator('button').filter({ hasText: label });
      await expect(btn).toBeVisible();
    }

    // "짧게" 선택
    const shortBtn = page.locator('button').filter({ hasText: '짧게' });
    await shortBtn.click();
    await expect(shortBtn).toHaveClass(/bg-primary/);
  });

  test('문체 옵션 4개 (대화체/설명체/캐주얼/전문가)', async ({ page }) => {
    const styles = ['대화체', '설명체', '캐주얼', '전문가'];

    for (const label of styles) {
      const btn = page.locator('button').filter({ hasText: label });
      await expect(btn).toBeVisible();
    }

    // "전문가" 선택
    const expertBtn = page.locator('button').filter({ hasText: '전문가' });
    await expertBtn.click();
    await expect(expertBtn).toHaveClass(/bg-primary/);
  });

  test('설정 유지 확인 (팝오버 닫았다 다시 열기)', async ({ page, contentGenerator }) => {
    // 스타일 "Q&A" 선택
    const qnaBtn = page.locator('button').filter({ hasText: 'Q&A' }).first();
    await qnaBtn.click();
    await expect(qnaBtn).toHaveClass(/bg-primary/);

    // 길이 "길게" 선택
    const longBtn = page.locator('button').filter({ hasText: '길게' });
    await longBtn.click();

    // 팝오버 닫기
    await contentGenerator.closeSettings();

    // 다시 열기
    await contentGenerator.openSettings();

    // 설정 유지 확인
    const qnaBtnAgain = page.locator('button').filter({ hasText: 'Q&A' }).first();
    await expect(qnaBtnAgain).toHaveClass(/bg-primary/);

    const longBtnAgain = page.locator('button').filter({ hasText: '길게' });
    await expect(longBtnAgain).toHaveClass(/bg-primary/);
  });
});
