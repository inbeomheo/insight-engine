/**
 * 스타일 옵션 테스트 (학습 엔진 UI — 4종 스타일 그리드)
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect } from '../fixtures/test-fixtures';

// 메인 그리드의 스타일 버튼 (aria-label: "<라벨> 스타일 선택: <설명>")
// 숨겨진 MobileAppShell이 같은 aria-label 버튼을 중복 렌더하므로 visible 필터 필수
const styleButtons = (page: import('@playwright/test').Page) =>
  page.getByRole('button', { name: /스타일 선택/ }).filter({ visible: true });

test.describe('스타일 옵션 @parallel @no-auth', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('출력 스타일 섹션이 표시됨', async ({ page }) => {
    // 섹션 헤딩: "출력 스타일 4"
    await expect(page.getByRole('heading', { name: /출력 스타일/ })).toBeVisible();

    // 스타일 버튼 4개 (요약/Q&A/퀴즈/리텐션 카드)
    await expect(styleButtons(page)).toHaveCount(4);
  });

  test('학습 스타일 4종이 모두 표시됨', async ({ page }) => {
    const buttons = styleButtons(page);

    // 라벨 + 설명이 각 버튼에 렌더됨
    await expect(buttons.filter({ hasText: '요약' }).first()).toContainText('핵심만 빠르게 정리');
    await expect(buttons.filter({ hasText: 'Q&A' }).first()).toContainText('질문과 답변 정리');
    await expect(buttons.filter({ hasText: '퀴즈' }).first()).toContainText('객관식 학습 문제');
    await expect(buttons.filter({ hasText: '리텐션 카드' }).first()).toContainText('반복 학습 카드');
  });

  test('스타일 선택이 변경됨 (다시 누르면 기본값 복귀)', async ({ page }) => {
    const summaryBtn = styleButtons(page).filter({ hasText: '요약' }).first();
    const quizBtn = styleButtons(page).filter({ hasText: '퀴즈' }).first();

    // 기본 선택은 요약
    await expect(summaryBtn).toHaveAttribute('aria-pressed', 'true');
    await expect(quizBtn).toHaveAttribute('aria-pressed', 'false');

    // 퀴즈 선택 → 퀴즈 활성, 요약 비활성
    await quizBtn.click();
    await expect(quizBtn).toHaveAttribute('aria-pressed', 'true');
    await expect(summaryBtn).toHaveAttribute('aria-pressed', 'false');

    // 퀴즈를 다시 누르면 기본값(요약)으로 복귀
    await quizBtn.click();
    await expect(summaryBtn).toHaveAttribute('aria-pressed', 'true');
    await expect(quizBtn).toHaveAttribute('aria-pressed', 'false');
  });

  test('각 스타일에 한국어 이름이 표시됨', async ({ page }) => {
    const texts = await styleButtons(page).allTextContents();
    expect(texts).toHaveLength(4);

    // 모든 스타일 버튼에 한국어 텍스트 포함 (Q&A도 설명이 한국어)
    const koreanPattern = /[가-힣]/;
    for (const text of texts) {
      expect(text).toMatch(koreanPattern);
    }
  });
});
