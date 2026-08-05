/**
 * 네트워크 에러 처리 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 *
 * 주의: /generate 요청은 오프라인 전환 또는 page.route 가로채기로 차단되므로
 * 실제 백엔드/AI 호출은 발생하지 않는다.
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('네트워크 에러 처리 @parallel', () => {
  test.setTimeout(60_000);

  test('오프라인 상태에서 적절한 에러 표시', async ({ context, page, mainPage, urlInput, contentGenerator }) => {
    await mainPage.goto();
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);

    // 오프라인으로 전환 (모델 자동 선택은 goto의 networkidle에서 이미 완료됨)
    await context.setOffline(true);

    // 생성 시도 → fetch 실패
    await contentGenerator.clickGenerate();

    // 에러 알림이 표시되어야 함 ('AI 모델을 선택해주세요' 같은 클라이언트 검증 에러가 아닌 네트워크 실패 메시지)
    const alert = page.getByRole('alert').filter({ hasText: /Failed to fetch|네트워크|오류|실패/ });
    await expect(alert).toBeVisible({ timeout: 15_000 });

    // 오프라인 복구
    await context.setOffline(false);

    // 에러 후 로딩 상태가 종료되어야 함
    expect(await contentGenerator.isLoading()).toBeFalsy();
  });

  test('서버 응답 지연 시 타임아웃 처리', async ({ page, mainPage, urlInput, contentGenerator }) => {
    await mainPage.goto();
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);

    // /generate 응답을 지연시킨 뒤 504로 종료 — 백엔드에 요청이 도달하지 않음
    await page.route('**/generate', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 3000));
      await route.fulfill({
        status: 504,
        contentType: 'application/json',
        body: JSON.stringify({ error: '[타임아웃] AI 응답 시간이 초과되었습니다.' }),
      });
    });

    // 생성 시작
    await contentGenerator.clickGenerate();

    // 응답 대기 중에는 로딩 스켈레톤이 표시되어야 함
    await expect(page.getByLabel('콘텐츠 생성 중').first()).toBeVisible({ timeout: 5_000 });

    // 타임아웃 에러가 사용자에게 표시되고 로딩이 종료되어야 함
    const alert = page.getByRole('alert').filter({ hasText: '타임아웃' });
    await expect(alert).toBeVisible({ timeout: 15_000 });
    await expect(page.getByLabel('콘텐츠 생성 중')).toHaveCount(0);
  });
});
