import { describe, expect, it } from 'vitest';
import { escapeHtml, sanitizeExportHtml } from './sanitizeExportHtml';

describe('sanitizeExportHtml', () => {
  it('removes executable tags, handlers, and dangerous URL schemes', () => {
    const dirty = [
      '<script>alert(1)</script>',
      '<img src=x onerror="alert(2)">',
      '<a href="javascript:alert(3)">bad</a>',
      '<svg><a xlink:href="javascript:alert(4)">x</a></svg>',
      '<meta http-equiv="refresh" content="0;url=javascript:alert(5)">',
      '<p>safe</p>',
    ].join('');

    const clean = sanitizeExportHtml(dirty);
    expect(clean).not.toMatch(/script|onerror|javascript:|<svg|<meta/i);
    expect(clean).toContain('<p>safe</p>');
  });

  it('escapes report titles before inserting them into an HTML document', () => {
    expect(escapeHtml('</title><script>alert(1)</script>')).toBe(
      '&lt;/title&gt;&lt;script&gt;alert(1)&lt;/script&gt;',
    );
  });
});
