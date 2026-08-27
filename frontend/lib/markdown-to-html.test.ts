import { describe, expect, it } from 'vitest';
import { injectTimestampLinks, markdownToHtml } from './markdown-to-html';

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

  it('독립 HTML에서도 렌더 가능한 self-contained MathML로 수식을 저장한다', async () => {
    const html = await markdownToHtml('$$x^2 + y^2$$');
    expect(html).toContain('<math');
    expect(html).toContain('<semantics>');
    expect(html).not.toContain('katex-html');
  });

  it('편집 저장 HTML에도 영상 타임코드 딥링크를 반영한다', async () => {
    const html = await markdownToHtml(
      '핵심 장면 [00:01:30]',
      'https://www.youtube.com/watch?v=abcdefghijk',
    );
    expect(html).toContain('t=90');
    expect(html).toContain('[00:01:30]');
  });

  it('기본 MM:SS 인용도 초 단위 딥링크로 변환한다', async () => {
    const html = await markdownToHtml(
      '핵심 장면 [03:25]',
      'https://www.youtube.com/watch?v=abcdefghijk',
    );
    expect(html).toContain('t=205');
    expect(html).toContain('[03:25]');
  });

  it('백엔드가 이미 링크한 인용을 중첩 링크로 다시 변환하지 않는다', () => {
    const linked = '[[03:25]](https://youtube.com/watch?v=abcdefghijk&t=205s)';
    const once = injectTimestampLinks(
      linked,
      'https://www.youtube.com/watch?v=abcdefghijk',
    );
    const twice = injectTimestampLinks(
      once,
      'https://www.youtube.com/watch?v=abcdefghijk',
    );
    expect(once).toBe(linked);
    expect(twice).toBe(linked);
  });
});
