import { describe, expect, it } from 'vitest';
import { markdownToHtml } from './markdown-to-html';

describe('markdownToHtml', () => {
  it('마크다운 제목/강조를 HTML 태그로 변환한다', async () => {
    const html = await markdownToHtml('# 제목\n\n**굵게** 그리고 *기울임*');
    expect(html).toContain('<h1>제목</h1>');
    expect(html).toContain('<strong>굵게</strong>');
    expect(html).toContain('<em>기울임</em>');
  });

  it('GFM 표를 변환한다 (remark-gfm 적용)', async () => {
    const html = await markdownToHtml('| a | b |\n| --- | --- |\n| 1 | 2 |');
    expect(html).toContain('<table>');
    expect(html).toContain('<td>1</td>');
  });

  it('빈 문자열이면 빈 HTML을 반환한다', async () => {
    expect(await markdownToHtml('')).toBe('');
  });
});
