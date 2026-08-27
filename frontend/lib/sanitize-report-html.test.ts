import { describe, expect, it } from 'vitest';
import { sanitizeReportHtml } from './sanitize-report-html';

describe('sanitizeReportHtml', () => {
  it('MathML 수식 구조와 접근성 annotation을 보존한다', () => {
    const sanitized = sanitizeReportHtml(
      '<span class="katex"><math display="block"><semantics><mrow>'
      + '<msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><mi>y</mi>'
      + '</mrow><annotation encoding="application/x-tex">x^2+y</annotation>'
      + '</semantics></math></span>',
    );

    expect(sanitized).toContain('<math display="block">');
    expect(sanitized).toContain('<msup>');
    expect(sanitized).toContain('encoding="application/x-tex"');
  });

  it('스크립트·이벤트 핸들러·위험 URL은 제거한다', () => {
    const sanitized = sanitizeReportHtml(
      '<math onclick="alert(1)"><mtext>safe</mtext></math>'
      + '<script>alert(1)</script><a href="javascript:alert(1)">bad</a>',
    );

    expect(sanitized).toContain('<math><mtext>safe</mtext></math>');
    expect(sanitized).not.toContain('onclick');
    expect(sanitized).not.toContain('<script');
    expect(sanitized).not.toContain('javascript:');
  });
});
