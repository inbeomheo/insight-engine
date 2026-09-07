import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import type { Page } from '@playwright/test';
import { test, expect, injectReports, makeMockReport } from '../fixtures/test-fixtures';

const SOURCE_URL = 'https://example.com/learning/agent-loop';
const NOTES = [
  { id: 'graph-source', title: '에이전트 실행', concept: '관찰과 행동' },
  { id: 'graph-target', title: '반복 학습', concept: '평가와 개선' },
  { id: 'graph-isolated', title: '독립 메모', concept: '기록' },
].map(({ id, title, concept }) => ({
  id,
  title,
  source: { type: 'text', url: '', title },
  key_concepts: [concept],
  summary: `${title}의 핵심 내용을 정리한 테스트 전용 노트입니다.`,
  tags: ['브라우저 검증'],
  created_at: '2026-09-01T09:00:00Z',
  language: 'ko',
  quotes: [],
  learning_points: [],
  review_questions: [],
  related_notes: [],
  quote_count: 0,
  learning_point_count: 0,
  review_question_count: 0,
}));

const QUIZ_CONTENT = `## 에이전트 학습 퀴즈

1. **질문**: 에이전트의 반복 구조는 무엇인가?
   A. 계획만 세운다
   B. 관찰하고 행동한 뒤 평가한다
   **정답**: B
   **해설**: 관찰, 행동, 평가를 반복한다.

2. **질문**: 도구 사용 전에 확인할 것은?
   A. 권한과 입력
   B. 화면 색상
   **정답**: A
   **해설**: 권한과 입력 경계를 먼저 확인한다.`;

const RETENTION_CONTENT = `## 반복 학습 카드

### 카드 1
**Recall**: 반복 학습의 목적은?
**Answer Key**: 배운 내용을 다시 떠올려 기억을 유지한다.

### 카드 2
**앞면**: 복습 후 확인할 것은?
**뒷면**: 기억하지 못한 개념을 확인한다.`;

async function isolateNoteResponses(page: Page) {
  // 브라우저 요청에만 응답하므로 공유 서버의 실제 노트를 읽거나 수정하지 않는다.
  await page.route('**/api/notes**', async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    expect(route.request().method()).toBe('GET');
    if (pathname === '/api/notes') {
      await route.fulfill({ json: { notes: NOTES } });
      return;
    }
    if (pathname === '/api/notes/graph') {
      await route.fulfill({ json: {
        nodes: NOTES.map(({ id, title, key_concepts, created_at }) => ({ id, title, key_concepts, created_at })),
        edges: [{ source: 'graph-source', target: 'graph-target', score: 0.87 }],
        meta: { node_limit: 50, edge_limit: 200, related_limit: 5, min_score: 0.5, node_count: 3, edge_count: 1 },
      } });
      return;
    }
    const match = pathname.match(/^\/api\/notes\/([^/]+)(\/backlinks)?$/);
    const note = NOTES.find(({ id }) => id === match?.[1]);
    if (!note) {
      await route.fulfill({ status: 404, json: { error: '테스트 노트 없음' } });
      return;
    }
    if (match?.[2]) {
      await route.fulfill({ json: { notes: note.id === 'graph-target'
        ? [{ id: 'graph-source', title: '에이전트 실행', score: 0.87 }]
        : [] } });
      return;
    }
    await route.fulfill({ json: note });
  });
}

test.describe('노트 관계 탐색과 Anki 내보내기', () => {
  test('목록에서 그래프 노드를 열고 역방향 연결로 다른 상세에 이동한다', async ({ page }) => {
    await injectReports(page, []);
    await isolateNoteResponses(page);
    await page.goto('/notes');
    await expect(page.getByRole('heading', { name: 'LLMWiki 홈' })).toBeVisible();
    await expect(page.getByRole('heading', { name: '반복 학습', exact: true })).toBeVisible();

    const tabs = page.getByRole('navigation', { name: '노트 보기 방식' });
    await expect(tabs.getByRole('link', { name: '목록', exact: true })).toHaveAttribute('aria-current', 'page');
    await tabs.getByRole('link', { name: '관계 그래프', exact: true }).click();
    await expect(page).toHaveURL(/\/notes\/graph$/);
    await expect(tabs.getByRole('link', { name: '관계 그래프', exact: true })).toHaveAttribute('aria-current', 'page');

    const graph = page.getByRole('region', { name: '지식 노트 관계 그래프' });
    await expect(graph.getByText('노드 3 · 연결 1', { exact: true })).toBeVisible();
    await expect(graph.getByRole('link', { name: / 노트 열기$/ })).toHaveCount(3);
    await expect(graph.getByRole('listitem')).toHaveCount(1);
    await expect(graph.getByRole('listitem')).toHaveText(/에이전트 실행\s*→\s*반복 학습\s*87%/);
    await graph.getByRole('link', { name: '반복 학습 노트 열기', exact: true }).click();

    await expect(page).toHaveURL(/\/notes\/graph-target$/);
    await expect(page.getByRole('heading', { name: '반복 학습', exact: true })).toBeVisible();
    const backlinks = page.getByRole('complementary', { name: '이 노트를 연결한 노트' });
    await expect(backlinks).toHaveCount(1);
    const incomingLink = backlinks.getByRole('link', { name: '에이전트 실행 87%' });
    await expect(incomingLink).toHaveAttribute('href', '/notes/graph-source');
    await incomingLink.click();

    await expect(page).toHaveURL(/\/notes\/graph-source$/);
    await expect(page.getByRole('heading', { name: '에이전트 실행', exact: true })).toBeVisible();
    await expect(backlinks.getByText('아직 이 노트를 가리키는 연결이 없습니다.')).toBeVisible();
    await expect(backlinks.getByRole('link')).toHaveCount(0);
  });

  test('Anki 메뉴는 퀴즈와 리텐션 카드에만 표시한다', async ({ page }) => {
    const styles = ['summary', 'quiz', 'retention_cards'];
    await injectReports(page, styles.map((style) => makeMockReport({
      id: `anki-menu-${style}`, style, title: `${style} 메뉴 확인`, url: '',
    })));
    await page.goto('/');

    for (const style of styles) {
      const card = page.locator(`[data-report-id="anki-menu-${style}"]`);
      await card.getByRole('button', { name: '더보기 메뉴' }).click();
      await expect(page.getByRole('menuitem', { name: '마크다운 (.md)', exact: true })).toBeVisible();
      const anki = page.getByRole('menuitem', { name: 'Anki 덱 (.apkg)', exact: true });
      if (style === 'summary') await expect(anki).toHaveCount(0);
      else await expect(anki).toBeVisible();
      await page.keyboard.press('Escape');
    }
  });

  for (const sample of [
    { style: 'quiz', title: '퀴즈 학습 덱', content: QUIZ_CONTENT,
      fronts: ['에이전트의 반복 구조는 무엇인가?', '도구 사용 전에 확인할 것은?'],
      backs: ['관찰, 행동, 평가를 반복한다.', '권한과 입력 경계를 먼저 확인한다.'] },
    { style: 'retention_cards', title: '리텐션 학습 덱', content: RETENTION_CONTENT,
      fronts: ['반복 학습의 목적은?', '복습 후 확인할 것은?'],
      backs: ['배운 내용을 다시 떠올려 기억을 유지한다.', '기억하지 못한 개념을 확인한다.'] },
  ]) {
    test(`${sample.style} 메뉴로 실제 Anki 패키지와 카드 내용을 내려받는다`, async ({ page }, testInfo) => {
      await injectReports(page, [makeMockReport({
        id: 'anki-download', ...sample, url: SOURCE_URL,
      })]);
      // 실제 브라우저 전송 본문을 로컬 Flask에 전달한다. AI 호출이나 원문 다운로드는 없다.
      await page.route('**/api/export/anki', async (route) => {
        const response = await page.request.post('http://127.0.0.1:5001/api/export/anki', {
          headers: { 'Content-Type': 'application/json', Origin: 'http://127.0.0.1:5001' },
          data: route.request().postData()!,
        });
        await route.fulfill({ response });
      });
      await page.goto('/');
      await page.locator('[data-report-id="anki-download"]').getByRole('button', { name: '더보기 메뉴' }).click();
      const requestPromise = page.waitForRequest((request) => new URL(request.url()).pathname === '/api/export/anki');
      const responsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/export/anki');
      const downloadPromise = page.waitForEvent('download');
      await page.getByRole('menuitem', { name: 'Anki 덱 (.apkg)', exact: true }).click();
      const request = await requestPromise;
      expect(request.method()).toBe('POST');
      expect(request.postDataJSON()).toEqual({
        title: sample.title, content: sample.content, style: sample.style,
        source_url: SOURCE_URL, tags: [sample.style, 'generated-content'],
      });
      const response = await responsePromise;
      expect(response.status()).toBe(200);
      expect(response.headers()['x-anki-card-count']).toBe('2');
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toBe(`${sample.title}.apkg`);
      expect(await download.failure()).toBeNull();
      const packagePath = testInfo.outputPath(`${sample.style}.apkg`);
      await download.saveAs(packagePath);

      // 표준 라이브러리로 압축을 읽고 메모리 SQLite(파일 내부 카드 저장소)만 조회한다.
      const packageData = JSON.parse(execFileSync(process.execPath, [
        resolve(__dirname, '../../../scripts/run_python.cjs'), '-c',
        'import json, sqlite3, sys, zipfile\n' +
        'with zipfile.ZipFile(sys.argv[1]) as package:\n' +
        '    names = package.namelist()\n' +
        '    connection = sqlite3.connect(":memory:")\n' +
        '    connection.deserialize(package.read("collection.anki2"))\n' +
        '    rows = connection.execute("SELECT flds, tags FROM notes ORDER BY id").fetchall()\n' +
        '    decks = json.loads(connection.execute("SELECT decks FROM col").fetchone()[0])\n' +
        '    print(json.dumps({"names": names, "rows": rows, "decks": list(decks.values()), "cards": connection.execute("SELECT COUNT(*) FROM cards").fetchone()[0]}, ensure_ascii=False))',
        packagePath,
      ], { encoding: 'utf8', timeout: 15_000 }));
      expect(packageData.names).toEqual(expect.arrayContaining(['collection.anki2', 'media']));
      expect(packageData.cards).toBe(2);
      expect(packageData.rows).toHaveLength(2);
      expect(packageData.decks).toEqual(expect.arrayContaining([expect.objectContaining({ name: sample.title })]));
      for (let index = 0; index < sample.fronts.length; index++) {
        const row = packageData.rows.find(([fields]: [string, string]) => fields.split('\u001f')[0].includes(sample.fronts[index]));
        expect(row, `카드 앞면: ${sample.fronts[index]}`).toBeDefined();
        const fields = row[0].split('\u001f');
        expect(fields[1]).toContain(sample.backs[index]);
        expect(fields[2]).toContain(SOURCE_URL);
        expect(row[1]).toContain(sample.style);
        expect(row[1]).toContain('generated-content');
      }
      await expect(page.getByText('Anki 덱 내보내기 완료', { exact: true })).toBeVisible();
    });
  }
});
