/**
 * 설정 UI 검증 테스트 (API 호출 없음)
 *
 * SettingsPopover의 모델/스타일/길이/문체 선택 UI 검증
 */
import { test, expect } from '../fixtures/test-fixtures';

test.describe('설정 UI (SettingsPopover)', () => {
  test.beforeEach(async ({ mainPage, contentGenerator }) => {
    await mainPage.goto();
    await contentGenerator.openSettings();
  });

  test('설정 팝오버 열기/닫기', async ({ page, contentGenerator }) => {
    const popover = page.getByRole('dialog', { name: '생성 설정' });

    // 이미 beforeEach에서 열려있음
    await expect(popover.getByText('AI 모델', { exact: true })).toBeVisible();
    await expect(popover.getByText(/^출력 스타일 \d+$/)).toBeVisible();
    await expect(popover.getByText('길이', { exact: true })).toBeVisible();
    await expect(popover.getByText('문체', { exact: true })).toBeVisible();

    // 닫기 (외부 클릭)
    await contentGenerator.closeSettings();
    await expect(popover).toBeHidden();
  });

  test('활성 서비스의 모델 목록 선택', async ({ page, contentGenerator }) => {
    const popover = page.getByRole('dialog', { name: '생성 설정' });
    const modelTrigger = popover.getByRole('combobox');
    await expect(modelTrigger).toHaveCount(1);

    // 현재 활성 서비스의 모델 드롭다운 열기
    await modelTrigger.click();

    // 프로바이더 옵션이 1개 이상 존재
    const options = page.getByRole('option');
    const count = await options.count();
    expect(count).toBeGreaterThanOrEqual(1);

    // 첫 번째 옵션 선택 (포탈 클릭으로 팝오버가 닫힐 수 있음)
    await options.first().click();

    // 팝오버가 닫혔으면 다시 열기
    if (!await popover.isVisible().catch(() => false)) {
      await contentGenerator.openSettings();
    }

    await expect(popover.getByRole('combobox')).toBeVisible();
  });

  test('4개 내장 학습 스타일 버튼 표시', async ({ page }) => {
    const popover = page.getByRole('dialog', { name: '생성 설정' });
    const expectedStyles = ['요약', 'Q&A', '퀴즈', '리텐션 카드'];

    for (const label of expectedStyles) {
      const btn = popover.locator(`button[aria-label^="${label} 스타일 선택"]`);
      await expect(btn).toBeVisible();
    }
  });

  test('스타일 선택 변경', async ({ page }) => {
    const popover = page.getByRole('dialog', { name: '생성 설정' });
    const qnaBtn = popover.getByRole('button', { name: /^Q&A 스타일 선택/ });
    await qnaBtn.click();

    await expect(qnaBtn).toHaveAttribute('aria-pressed', 'true');

    // 다른 스타일 클릭 시 이전 선택 해제
    const quizBtn = popover.getByRole('button', { name: /^퀴즈 스타일 선택/ });
    await quizBtn.click();

    await expect(quizBtn).toHaveAttribute('aria-pressed', 'true');
    await expect(qnaBtn).toHaveAttribute('aria-pressed', 'false');
  });

  test('길이 옵션 3개 (짧게/보통/길게)', async ({ page }) => {
    const popover = page.getByRole('dialog', { name: '생성 설정' });
    const lengths = ['짧게', '보통', '길게'];

    for (const label of lengths) {
      const btn = popover.getByRole('button', { name: `${label} 길이 선택` });
      await expect(btn).toBeVisible();
    }

    // "짧게" 선택
    const shortBtn = popover.getByRole('button', { name: '짧게 길이 선택' });
    await shortBtn.click();
    await expect(shortBtn).toHaveAttribute('aria-pressed', 'true');
  });

  test('문체 옵션 4개 (대화체/설명체/캐주얼/전문가)', async ({ page }) => {
    const popover = page.getByRole('dialog', { name: '생성 설정' });
    const styles = ['대화체', '설명체', '캐주얼', '전문가'];

    for (const label of styles) {
      const btn = popover.getByRole('button', { name: `${label} 문체 선택` });
      await expect(btn).toBeVisible();
    }

    // "전문가" 선택
    const expertBtn = popover.getByRole('button', { name: '전문가 문체 선택' });
    await expertBtn.click();
    await expect(expertBtn).toHaveAttribute('aria-pressed', 'true');
  });

  test('설정 유지 확인 (팝오버 닫았다 다시 열기)', async ({ page, contentGenerator }) => {
    const popover = page.getByRole('dialog', { name: '생성 설정' });

    // 스타일 "Q&A" 선택
    const qnaBtn = popover.getByRole('button', { name: /^Q&A 스타일 선택/ });
    await qnaBtn.click();
    await expect(qnaBtn).toHaveAttribute('aria-pressed', 'true');

    // 길이 "길게" 선택
    const longBtn = popover.getByRole('button', { name: '길게 길이 선택' });
    await longBtn.click();
    await expect(longBtn).toHaveAttribute('aria-pressed', 'true');

    // 팝오버 닫기
    await contentGenerator.closeSettings();

    // 다시 열기
    await contentGenerator.openSettings();

    // 설정 유지 확인
    const qnaBtnAgain = popover.getByRole('button', { name: /^Q&A 스타일 선택/ });
    await expect(qnaBtnAgain).toHaveAttribute('aria-pressed', 'true');

    const longBtnAgain = popover.getByRole('button', { name: '길게 길이 선택' });
    await expect(longBtnAgain).toHaveAttribute('aria-pressed', 'true');
  });
});
