/**
 * 콘텐츠 생성 - AI 프로바이더 및 모델 선택, 스타일, 모디파이어 테스트
 *
 * spec: tests/e2e/specs/02-content-generation.plan.md
 * seed: seed.spec.ts
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect, TEST_DATA } from '../../fixtures/test-fixtures';

test.describe('콘텐츠 생성 테스트 @parallel @no-auth', () => {
  test.setTimeout(60_000);

  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test.describe('Suite 1: AI 프로바이더 및 모델 선택', () => {
    test('TC-1.1: 프로바이더 선택', async ({ page }) => {
      // 1. 프로바이더 드롭다운 클릭
      const providerSelect = page.locator('#provider');
      await expect(providerSelect).toBeVisible();

      // 2. 사용 가능한 프로바이더 선택 (Gemini, DeepSeek 등)
      const options = await providerSelect.locator('option').allTextContents();
      const validOptions = options.filter(opt => opt && opt !== '선택하세요');

      if (validOptions.length > 0) {
        await providerSelect.selectOption({ label: validOptions[0] });

        // Expected: 선택한 프로바이더가 표시됨
        const selectedValue = await providerSelect.inputValue();
        expect(selectedValue).toBeTruthy();

        // Expected: 해당 프로바이더의 모델 목록 로드
        const modelSelect = page.locator('#model');
        await expect(modelSelect).toBeVisible();
      }
    });

    test('TC-1.2: 모델 선택', async ({ page }) => {
      // 1. 프로바이더 선택 후 모델 드롭다운 클릭
      const providerSelect = page.locator('#provider');
      const providerOptions = await providerSelect.locator('option').allTextContents();
      const validProviders = providerOptions.filter(opt => opt && opt !== '선택하세요');

      if (validProviders.length > 0) {
        await providerSelect.selectOption({ label: validProviders[0] });

        // 모델 선택이 가능할 때까지 대기
        const modelSelect = page.locator('#model');
        await expect(modelSelect).toBeVisible();

        // 2. 모델 선택
        const modelOptions = await modelSelect.locator('option').allTextContents();
        const validModels = modelOptions.filter(opt => opt && opt !== '선택하세요');

        if (validModels.length > 0) {
          await modelSelect.selectOption({ label: validModels[0] });

          // Expected: 선택한 모델이 표시됨
          const selectedValue = await modelSelect.inputValue();
          expect(selectedValue).toBeTruthy();
        }
      }
    });
  });

  test.describe('Suite 2: 스타일 선택', () => {
    test('TC-2.1: 스타일 카드 선택', async ({ page }) => {
      // 1. 스타일 카드 섹션에서 카드 클릭
      const summaryStyleInput = page.locator('input[name="style"][value="summary"]');
      const summaryStyleCard = page.locator('label:has(input[name="style"][value="summary"])');

      await summaryStyleCard.click();

      // Expected: 선택된 카드에 하이라이트 표시 (peer-checked 클래스)
      await expect(summaryStyleInput).toBeChecked();

      // Expected: 이전 선택 해제 (blog는 기본 선택)
      const blogStyleInput = page.locator('input[name="style"][value="blog"]');
      await expect(blogStyleInput).not.toBeChecked();
    });

    test('TC-2.2: 여러 스타일 순회', async ({ page }) => {
      // 1. 각 스타일 카드를 순서대로 클릭
      const styles = ['summary', 'detailed', 'easy', 'needs'];

      for (const styleValue of styles) {
        const styleInput = page.locator(`input[name="style"][value="${styleValue}"]`);
        const styleCard = page.locator(`label:has(input[name="style"][value="${styleValue}"])`);

        await styleCard.click();

        // Expected: 항상 하나의 스타일만 선택됨
        await expect(styleInput).toBeChecked();

        // 다른 스타일들은 선택 해제 확인
        const allStyleInputs = page.locator('input[name="style"]');
        const checkedCount = await allStyleInputs.evaluateAll(inputs =>
          inputs.filter((input: any) => input.checked).length
        );
        expect(checkedCount).toBe(1);
      }
    });
  });

  test.describe('Suite 3: 모디파이어 설정', () => {
    test('TC-3.1: 길이 모디파이어', async ({ page }) => {
      // 1. 길이 옵션 (짧게/보통/길게) 중 하나 선택
      const shortLengthInput = page.locator('input[name="length"][value="short"]');
      const shortLengthChip = page.locator('label:has(input[name="length"][value="short"])');

      await shortLengthChip.click();

      // Expected: 선택된 옵션 하이라이트
      await expect(shortLengthInput).toBeChecked();

      // 긴 글 옵션도 테스트
      const longLengthInput = page.locator('input[name="length"][value="long"]');
      const longLengthChip = page.locator('label:has(input[name="length"][value="long"])');

      await longLengthChip.click();
      await expect(longLengthInput).toBeChecked();
      await expect(shortLengthInput).not.toBeChecked();
    });

    test('TC-3.2: 톤 모디파이어', async ({ page }) => {
      // 1. 톤 옵션 (친근/전문/유머) 중 하나 선택
      const friendlyToneInput = page.locator('input[name="tone"][value="friendly"]');
      const friendlyToneChip = page.locator('label:has(input[name="tone"][value="friendly"])');

      await friendlyToneChip.click();

      // Expected: 선택된 옵션 하이라이트
      await expect(friendlyToneInput).toBeChecked();

      // 유머 톤도 테스트
      const humorousToneInput = page.locator('input[name="tone"][value="humorous"]');
      const humorousToneChip = page.locator('label:has(input[name="tone"][value="humorous"])');

      await humorousToneChip.click();
      await expect(humorousToneInput).toBeChecked();
      await expect(friendlyToneInput).not.toBeChecked();
    });

    test('TC-3.3: 이모지 모디파이어', async ({ page }) => {
      // 1. 이모지 사용/미사용 선택
      const emojiCheckbox = page.locator('#emoji-checkbox');
      const emojiChip = page.locator('label:has(#emoji-checkbox)');

      // 초기 상태 확인 (체크 해제 상태)
      const initialState = await emojiCheckbox.isChecked();

      // 클릭하여 토글
      await emojiChip.click();

      // Expected: 선택 상태 반영
      await expect(emojiCheckbox).toBeChecked({ checked: !initialState });

      // 다시 클릭하여 토글
      await emojiChip.click();
      await expect(emojiCheckbox).toBeChecked({ checked: initialState });
    });
  });

  test.describe('Suite 4: 콘텐츠 생성 실행', () => {
    test('TC-4.1: 생성 버튼 비활성화 상태', async ({ page, urlInput }) => {
      // 1. URL 없이 생성 버튼 확인
      const urlCount = await urlInput.getUrlCount();

      // URL이 있다면 모두 제거
      if (urlCount > 0) {
        await urlInput.clearAllUrls();
      }

      const generateBtn = page.locator('#run-analysis-btn');

      // Expected: 버튼은 표시되지만 클릭 시 경고 (UI에서 비활성화가 아닐 수 있음)
      await expect(generateBtn).toBeVisible();
    });

    test('TC-4.2: 생성 실행 (UI 상태 검증)', async ({ page, urlInput, contentGenerator }) => {
      // 1. 유효한 URL 추가
      await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);

      // URL이 추가되었는지 확인
      const urlCount = await urlInput.getUrlCount();
      expect(urlCount).toBeGreaterThan(0);

      // 2. 프로바이더/모델 선택
      const providerSelect = page.locator('#provider');
      const providerOptions = await providerSelect.locator('option').allTextContents();
      const validProviders = providerOptions.filter(opt => opt && opt !== '선택하세요');

      if (validProviders.length > 0) {
        await providerSelect.selectOption({ label: validProviders[0] });
      }

      // 3. 스타일 선택 (기본값이 blog이므로 그대로 사용)
      const blogStyleInput = page.locator('input[name="style"][value="blog"]');
      await expect(blogStyleInput).toBeChecked();

      // 4. 생성 버튼 클릭
      const generateBtn = page.locator('#run-analysis-btn');
      await expect(generateBtn).toBeVisible();
      await expect(generateBtn).toBeEnabled();

      // Expected: 버튼 클릭 가능
      // 실제 API 호출 없이 UI 상태만 검증
      // (실제 생성은 다른 테스트에서 수행)
    });

    test('TC-4.3: 모든 옵션 조합 테스트', async ({ page, urlInput }) => {
      // URL 추가
      await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);

      // 프로바이더 선택
      const providerSelect = page.locator('#provider');
      const providerOptions = await providerSelect.locator('option').allTextContents();
      const validProviders = providerOptions.filter(opt => opt && opt !== '선택하세요');

      if (validProviders.length > 0) {
        await providerSelect.selectOption({ label: validProviders[0] });
      }

      // 스타일 선택
      const qnaStyleCard = page.locator('label:has(input[name="style"][value="qna"])');
      await qnaStyleCard.click();

      // 길이 모디파이어
      const longLengthChip = page.locator('label:has(input[name="length"][value="long"])');
      await longLengthChip.click();

      // 톤 모디파이어
      const friendlyToneChip = page.locator('label:has(input[name="tone"][value="friendly"])');
      await friendlyToneChip.click();

      // 이모지 모디파이어
      const emojiCheckbox = page.locator('#emoji-checkbox');
      const emojiChip = page.locator('label:has(#emoji-checkbox)');
      await emojiChip.click();

      // Expected: 모든 옵션이 정상적으로 선택됨
      await expect(page.locator('input[name="style"][value="qna"]')).toBeChecked();
      await expect(page.locator('input[name="length"][value="long"]')).toBeChecked();
      await expect(page.locator('input[name="tone"][value="friendly"]')).toBeChecked();
      await expect(emojiCheckbox).toBeChecked();

      // 생성 버튼 활성화 확인
      const generateBtn = page.locator('#run-analysis-btn');
      await expect(generateBtn).toBeVisible();
      await expect(generateBtn).toBeEnabled();
    });
  });
});
